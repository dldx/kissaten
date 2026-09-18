"""Coffea Cafés Especiales scraper implementation with AI-powered extraction.

Platform: Lovable/React single-page app (Vite bundle) — there is no per-product
storefront route and the ``/cafes`` catalogue data is bundled client-side. The catalogue
renders one ``button.group`` card per coffee; clicking a card opens a ``[role="dialog"]``
detail panel containing producer, tasting notes, process, elevation, variety and process
detail. Each card carries a stable id taken from its image filename
(``/__l5e/.../<id>.png``), which we use to build synthetic per-coffee URLs
(``https://www.coffea.gt/cafes/<id>``) that map back to the rendered dialog.
There is no online checkout: individual coffees show availability only
("DISPONIBLE AHORA" / "DE REGRESO PRONTO") and The Fermentation Project kit is reserved
via a form at ``/fermentationproject`` (Q450). Model scraper used: ``koppi.py`` with a
Playwright dialog-narrowing ``fetch_page`` override.
"""

import logging

from bs4 import BeautifulSoup

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)

BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

CAFES_URL = "https://www.coffea.gt/cafes"
FERMENTATION_PROJECT_URL = "https://www.coffea.gt/fermentationproject"


@register_scraper(
    name="coffea-cafes-especiales",
    display_name="Coffea Cafés Especiales",
    roaster_name="Coffea Cafés Especiales",
    website="https://www.coffea.gt",
    description=(
        "Specialty coffee roaster and café in Antigua Guatemala, roasting Guatemalan "
        "microlots and the Coffea edition of The Fermentation Project."
    ),
    requires_api_key=True,
    currency="GTQ",
    country="Guatemala",
    status="experimental",
)
class CoffeaEspecialesScraper(BaseScraper):
    """Scraper for Coffea Cafés Especiales (coffea.gt) with AI extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Coffea Cafés Especiales scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Coffea Cafés Especiales",
            base_url="https://www.coffea.gt",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=45.0,
        )

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get the coffee catalogue (SPA) URL."""
        return [CAFES_URL]

    async def _fetch_with_playwright(self, url: str) -> str:
        """Render the SPA with Playwright using a real browser UA."""
        browser = await self._get_browser()
        page = await browser.new_page(viewport={"width": 1440, "height": 900})

        try:
            await page.set_extra_http_headers(
                {
                    "User-Agent": BROWSER_USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "es-ES,es;q=0.9,en;q=0.5",
                }
            )
            response = await page.goto(url, timeout=self.timeout * 1000, wait_until="domcontentloaded")
            if not response or not response.ok:
                raise Exception(f"Failed to load page: {response.status if response else 'No response'}")

            # React needs a moment to paint the catalogue / kit content.
            if "/cafes" in url:
                try:
                    await page.wait_for_selector("button.group", timeout=15000)
                except Exception:
                    await page.wait_for_timeout(5000)
            else:
                await page.wait_for_timeout(4000)
            return await page.content()

        finally:
            await page.close()

    async def _fetch_coffee_dialog(self, url: str) -> BeautifulSoup | None:
        """Render ``/cafes``, click the matching card and return the detail dialog HTML.

        The catalogue has no per-product routes, so synthetic URLs
        ``/cafes/<id>`` are mapped to the card whose image filename matches ``<id>``;
        clicking it opens the ``[role="dialog"]`` detail panel. Returning only the
        dialog means the AI extractor sees just the coffee's structured facts.
        """
        coffee_id = url.rstrip("/").rsplit("/", 1)[-1]
        browser = await self._get_browser()
        page = await browser.new_page(viewport={"width": 1440, "height": 900})

        try:
            await page.set_extra_http_headers(
                {
                    "User-Agent": BROWSER_USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "es-ES,es;q=0.9,en;q=0.5",
                }
            )
            await page.goto(CAFES_URL, timeout=self.timeout * 1000, wait_until="domcontentloaded")
            card = page.locator(f'button.group:has(img[src*="{coffee_id}"])').first
            await card.wait_for(timeout=20000)
            await card.click()
            dialog = page.locator('[role="dialog"]').first
            await dialog.wait_for(timeout=15000)
            await page.wait_for_timeout(800)
            dialog_html = await dialog.evaluate("el => el.outerHTML")
            if not dialog_html:
                return None
            return BeautifulSoup(dialog_html, "lxml")

        except Exception as e:
            logger.error(f"Error opening coffee dialog for {url}: {e}")
            return None

        finally:
            await page.close()

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | None:
        """Fetch a page, forcing Playwright and narrowing synthetic coffee URLs to the dialog."""
        url = kwargs.get("url") or (args[0] if args else "")
        try:
            kwargs = {k: v for k, v in kwargs.items() if k != "url"}
            kwargs["use_playwright"] = True
            # Synthetic per-coffee URL: render the dialog instead of the raw page.
            if "/cafes/" in url:
                return await self._fetch_coffee_dialog(url)
            return await super().fetch_page(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error fetching page {url}: {e}")
            return None

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract coffee URLs from the SPA catalogue.

        # Sold-out detection: card-level text detection on each ``button.group`` card.
        Coffea labels out-of-stock coffees "DE REGRESO PRONTO" ("back soon") versus
        "DISPONIBLE AHORA" ("available now"); those cards are skipped and become
        out-of-stock diffjson updates against history. Applied before the exclusion
        filter.

        Synthetic ``/cafes/<id>`` URLs are used because the SPA has no per-product
        routes; the Fermentation Project tasting kit page is appended explicitly so it
        is extracted too (it is flagged downstream by the tasting-kit pipeline).
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        product_urls: list[str] = []
        seen: set[str] = set()
        for card in soup.select("button.group"):
            img = card.select_one("img")
            src = img.get("src") if img else None
            if not src or not isinstance(src, str):
                continue
            coffee_id = src.rsplit("/", 1)[-1].rsplit(".", 1)[0]
            if not coffee_id:
                continue

            card_text = " ".join(card.get_text(" ", strip=True).split()).lower()
            if "de regreso pronto" in card_text or "agotado" in card_text:
                logger.debug(f"Skipping unavailable coffee card: {coffee_id}")
                continue

            url = f"{CAFES_URL}/{coffee_id}"
            if url not in seen:
                seen.add(url)
                product_urls.append(url)

        # The Fermentation Project kit lives on its own SPA route (not linked from the
        # catalogue grid) and must be extracted.
        if FERMENTATION_PROJECT_URL not in seen:
            product_urls.append(FERMENTATION_PROJECT_URL)

        logger.info(f"Found {len(product_urls)} coffee/kit URLs from {store_url}")
        return product_urls

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction (Spanish → English)."""
        if not product_urls:
            return []

        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=True,
            use_optimized_mode=False,
            translate_to_english=True,
        )

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Pin GTQ — the registry default-currency lookup falls back to GBP for hyphenated names."""
        bean.currency = "GTQ"
        return bean
