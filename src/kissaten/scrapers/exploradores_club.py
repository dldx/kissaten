"""Exploradores Club de Cafe scraper implementation with AI extraction.

Exploradores De Café (grupoexploradores.com) is a specialty coffee club and
roastery based in Mexico City (Av. Santa Fe, CDMX — verified from the site's
Squarespace location data and es-MX locale; prices are in MXN despite the
roaster's Guatemalan group heritage).

Discovery notes (2026-09, curl-first):
- Platform: Squarespace. ``products.json`` 404s (not Shopify).
- The main ``/tienda`` listing mixes coffee with a large amount of equipment
  (Acaia scales, Fellow gear, Ascaso machines, ...). Coffee lives in dedicated
  collections: ``/tienda/caf-especialidad``, ``/tienda/caf-orgnico`` and
  ``/tienda/caf-descafeinado`` — we crawl those instead of filtering the
  83-product mega listing.
- Product URLs are ``/tienda/p/<slug>``; each collection renders all its
  products on one page (no pagination).
- Product pages expose ``og:title`` / ``product:price:amount`` /
  ``product:price:currency`` (MXN) meta tags plus a
  ``<script data-name="static-context">`` blob with per-variant
  presentación/molienda/price/stock data.
- Sold-out products show "Agotado" on their ``div.product-list-item`` card and
  carry a ``sold-out`` modifier class.
- The James Hoffmann x Luca Solís "The Fermentation Project" kit de cata lives
  in the caf-especialidad collection (currently sold out) and must be extracted.
"""

import json
import logging
import re
from pathlib import Path

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)

STORE_URLS = [
    "https://www.grupoexploradores.com/tienda/caf-especialidad",
    "https://www.grupoexploradores.com/tienda/caf-orgnico",
    "https://www.grupoexploradores.com/tienda/caf-descafeinado",
]

# Defensive exclusions in case non-coffee items appear in the coffee
# collections (suscripción = subscription, tarjeta de regalo = gift card,
# báscula = scale, molino = grinder, tetera/hervidor = kettle, ...).
# The curated "kit-de-cafe-*" and Fermentation Project kits are NOT excluded.
EXCLUDED_URL_PATTERNS = [
    "suscripcion",
    "tarjeta-de-regalo",
    "bascula",
    "molino",
    "dripper",
    "hervidor",
    "tetera",
    "filtros",
    "capsulas",
    "tote-bag",
    "playera",
    "kit-de-accesorios",
    "caja-de-drippers",
]


@register_scraper(
    name="exploradores-club-de-cafe",
    display_name="Exploradores Club de Cafe",
    roaster_name="Exploradores Club de Cafe",
    website="https://www.grupoexploradores.com",
    description=(
        "Mexico City specialty coffee club and roaster sourcing and roasting "
        "experimental Latin American lots, including fermentation-project kits."
    ),
    requires_api_key=True,
    currency="MXN",
    country="Mexico",
    status="experimental",
)
class ExploradoresClubScraper(BaseScraper):
    """Scraper for Exploradores De Café (grupoexploradores.com) — Squarespace.

    Model: ``pala_kaffebrenneri.py`` — Squarespace product-page meta tags plus
    the parsed static-context variants JSON alongside page screenshots.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Exploradores Club de Cafe scraper."""
        super().__init__(
            roaster_name="Exploradores Club de Cafe",
            base_url="https://www.grupoexploradores.com",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Return the coffee collection URLs (each renders on a single page)."""
        return list(STORE_URLS)

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract coffee product URLs from a Squarespace coffee collection.

        Args:
            store_url: Coffee collection URL

        Returns:
            List of in-stock coffee product URLs
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        product_urls = []
        for card in soup.select("div.product-list-item"):
            link = card.select_one("a.product-list-item-link") or card.find("a", href=True)
            if not link or not link.get("href"):
                continue
            url = self.resolve_url(link["href"])

            # Sold-out detection: text check ("Agotado") plus the Squarespace
            # "sold-out" modifier class on each div.product-list-item card.
            card_text = " ".join(card.get_text(" ", strip=True).split()).lower()
            classes = card.get("class", [])
            if ("agotado" in card_text or "sold out" in card_text or "sold-out" in classes) and not (
                self._keep_sold_out_fermentation_kit(url)
            ):
                logger.debug(f"Skipping sold-out product card: {url}")
                continue

            product_urls.append(url)

        product_urls = list(dict.fromkeys(product_urls))

        coffee_urls = [
            url
            for url in product_urls
            if self.is_coffee_product_url(url, required_path_patterns=["/tienda/p/"])
            and not any(ex in url.lower() for ex in EXCLUDED_URL_PATTERNS)
        ]
        logger.info(f"Found {len(coffee_urls)} coffee product URLs out of {len(product_urls)} total from {store_url}")
        return coffee_urls

    def _keep_sold_out_fermentation_kit(self, url: str) -> bool:
        """Keep the Fermentation Project kit de cata in the list while sold out.

        The tasting kit must be extracted so it enters the tasting-kit review
        flow downstream. Once scraped historically it drops out of the current
        URL list so the next refresh marks it out of stock via diffjson.
        """
        if "the-fermentation-project" not in url.lower():
            return False
        self._load_existing_beans_from_all_sessions(Path("data"))
        return not self._is_bean_already_scraped_historically(url)

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction + page screenshot."""
        if not product_urls:
            return []

        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=False,
            use_optimized_mode=True,  # Send a page screenshot for visual/roast info
            translate_to_english=True,  # Spanish site — translate to English
        )

    async def take_screenshot(self, url: str, full_page: bool = True) -> bytes | None:
        """Take screenshot after dismissing the Squarespace cookie banner."""
        browser = await self._get_browser()
        page = await browser.new_page()

        try:
            signed_headers = self.get_signed_headers(url)
            headers_to_set = {**self.headers, **signed_headers}
            await page.set_extra_http_headers(headers_to_set)

            response = await page.goto(url, timeout=self.timeout * 1000, wait_until="networkidle")

            if not response or not response.ok:
                raise Exception(f"Failed to load page: {response.status if response else 'No response'}")

            # Dismiss Squarespace cookie banner if present
            try:
                accept_btn = await page.wait_for_selector(".sqs-cookie-banner-v2-accept, button.accept", timeout=3000)
                if accept_btn:
                    await accept_btn.click()
                    await page.wait_for_timeout(1000)
            except Exception as e:
                logger.debug(f"No cookie banner dismissed: {e}")

            # Remove related products section before taking screenshot
            try:
                await page.evaluate("""() => {
                    const els = document.querySelectorAll('div.product-related-products, .related-products');
                    els.forEach(el => el.remove());
                }""")
            except Exception as e:
                logger.debug(f"Could not remove related products section: {e}")

            # Trigger scroll for lazy-loaded assets
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1000)
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(500)

            return await page.screenshot(full_page=full_page, type="png")

        except Exception as e:
            logger.error(f"Failed to take screenshot of {url}: {e}")
            return None

        finally:
            await page.close()

    async def fetch_page(self, *args, **kwargs):
        """Send the product-page meta tags plus the parsed size/price variants to
        the extractor — visual/roast info comes from the page screenshot."""
        soup = await super().fetch_page(*args, **kwargs)
        url = kwargs.get("url") or (args[0] if args else "")
        if "/tienda/p/" not in url:
            return soup

        return self._compact_product_soup(soup)

    @staticmethod
    def _compact_product_soup(soup: BeautifulSoup | None) -> BeautifulSoup | None:
        """Reduce a Squarespace product page to its meta tags and variants text.

        The og:* / product:* meta tags carry name, description, price, currency
        and availability; per-variant presentación/molienda/stock data is parsed
        from the ``Static.SQUARESPACE_CONTEXT`` script. The screenshot carries
        the rest.
        """
        if soup is None:
            return None

        compact = BeautifulSoup("<html><head></head><body></body></html>", "html.parser")
        keep_meta = {
            "og:title",
            "og:description",
            "og:url",
            "og:type",
            "product:price:amount",
            "product:price:currency",
            "product:availability",
        }
        for meta in soup.find_all("meta"):
            key = meta.get("property") or meta.get("itemprop") or meta.get("name")
            if key in keep_meta or meta.get("name") == "description":
                compact.head.append(meta)

        compact.body.append(ExploradoresClubScraper._extract_variants(soup))
        return compact

    @staticmethod
    def _extract_variants(soup: BeautifulSoup) -> Tag:
        """Parse the Squarespace static-context script for per-variant size/price.

        Squarespace embeds the product's variants (presentación, molienda,
        price, currency, stock) inside a ``<script data-name="static-context">``
        as the JSON blob ``Static.SQUARESPACE_CONTEXT = {...}``. We surface
        those alongside the meta tags so the AI can record the size and price
        per variant accurately.
        """
        container = BeautifulSoup("<div></div>", "html.parser").div
        script = soup.find("script", {"data-name": "static-context"})
        if script is None:
            return container

        blob = script.string or script.get_text() or ""
        match = re.search(r"Static\.SQUARESPACE_CONTEXT\s*=\s*(\{.*?\})\s*;", blob, re.DOTALL)
        if not match:
            return container

        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError:
            return container

        product = data.get("product") or {}
        variants = product.get("variants") or []
        if not variants:
            return container

        lines = ["Variants:"]
        for v in variants:
            attrs = v.get("attributes") or {}
            size = "; ".join(str(val) for val in attrs.values()) or "n/a"
            price = (v.get("price") or {}).get("decimalValue")
            currency = (v.get("price") or {}).get("currencyCode")
            stock = "instock" if (v.get("stock") or {}).get("unlimited") else "unknown"
            lines.append(f"- Size: {size} | Price: {price} {currency} | Stock: {stock}")

        container.string = "\n".join(lines)
        return container

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Pin MXN as the store currency (Squarespace emits product:price:currency
        rather than og:price:currency, so the generic detection can miss it)."""
        bean.currency = "MXN"
        return bean

    def _get_tasting_kit_url_patterns(self) -> list[str]:
        """Add the Spanish tasting-kit slugs used by this roaster."""
        return super()._get_tasting_kit_url_patterns() + [
            "kit-de-cafe",  # curated coffee kit
            "the-fermentation-project",
            "kit-de-cata",
        ]
