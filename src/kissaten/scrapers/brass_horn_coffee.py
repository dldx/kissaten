"""Brass Horn Coffee Roasters scraper implementation with AI-powered extraction.

Platform: Square Online (``<meta name="generator" content="Square Online"/>``).
Listing and product detail pages are client-rendered Vue apps served from a ~560-byte
HTML shell, so both need Playwright. Product detail content lives inside
``div.product-detail-page``; the category listing is ``/shop/coffee/2`` (Square
category id 2) and sold-out products are hidden from that listing. Model scraper used:
``sw_roasting.py`` (Square Online, ``div.product-detail-page`` narrowing, Playwright
with a real browser User-Agent).
"""

import logging

from bs4 import BeautifulSoup
from playwright.async_api import Page

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)

# Square Online blocks headless/bot User-Agents and only renders products for a
# real browser UA (verified via curl/Playwright discovery).
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def _has_product_class(classes) -> bool:
    """Match ancestors whose class list contains a 'product' token (bs4 passes str or list)."""
    if not classes:
        return False
    joined = classes if isinstance(classes, str) else " ".join(classes)
    return "product" in joined.lower()


@register_scraper(
    name="brass-horn-coffee",
    display_name="Brass Horn Coffee Roasters",
    roaster_name="Brass Horn Coffee Roasters",
    website="https://www.brasshorncoffee.com",
    description=(
        "Specialty coffee roaster and café in Murfreesboro, Tennessee, selling "
        "single-origin microlots, blends and a roasters-choice sample box."
    ),
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class BrassHornCoffeeScraper(BaseScraper):
    """Scraper for Brass Horn Coffee Roasters (brasshorncoffee.com) with AI extraction."""

    #: Square Online category listing for the "Coffee" category (id 2).
    STORE_URL = "https://www.brasshorncoffee.com/shop/coffee/2"

    def __init__(self, api_key: str | None = None):
        """Initialize Brass Horn Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Brass Horn Coffee Roasters",
            base_url="https://www.brasshorncoffee.com",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=45.0,
        )

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get the coffee category listing URL."""
        return [self.STORE_URL]

    async def _fetch_with_playwright(self, url: str) -> str:
        """Render a Square Online page with Playwright using a real browser UA.

        Square Online only renders the Vue storefront for browser-like User-Agents
        (the default headless/bot UA returns an empty shell) and takes several
        seconds to hydrate the product content, so we wait for the relevant markers
        instead of relying on the base ``_fetch_with_playwright`` 1s wait.
        """
        browser = await self._get_browser()
        # Square Online only renders product content for desktop-sized viewports.
        page: Page = await browser.new_page(viewport={"width": 1440, "height": 900})

        try:
            await page.set_extra_http_headers(
                {
                    "User-Agent": BROWSER_USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                }
            )

            response = await page.goto(url, timeout=self.timeout * 1000, wait_until="domcontentloaded")
            if not response or not response.ok:
                raise Exception(f"Failed to load page: {response.status if response else 'No response'}")

            # Wait for the hydration marker that fits the page type.
            if "/product/" in url:
                selector = "div.product-detail-page"
            else:
                selector = 'a[href*="/product/"]'
            try:
                await page.wait_for_selector(selector, timeout=20000)
            except Exception:
                logger.warning(f"Timed out waiting for '{selector}' on {url}")
                await page.wait_for_timeout(5000)

            return await page.content()

        finally:
            await page.close()

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | None:
        """Fetch a Square Online page.

        Category listings are rendered with Playwright and scrolled until the lazy
        product grid stops growing; product detail pages are rendered and narrowed to
        the single stable ``div.product-detail-page`` container (``sw_roasting`` model).
        """
        url = kwargs.get("url") or (args[0] if args else "")
        try:
            if "/product/" not in url:
                return await self._fetch_listing_with_scroll(url)

            kwargs = {k: v for k, v in kwargs.items() if k != "url"}
            kwargs["use_playwright"] = True
            soup = await super().fetch_page(*args, **kwargs)
            if soup is None:
                return None
            product_el = soup.select("div.product-detail-page")
            if len(product_el) == 1:
                logger.debug(f"Narrowed soup to div.product-detail-page for {url}")
                return product_el[0]
            logger.warning(f"Expected 1 div.product-detail-page for {url}, found {len(product_el)}")
            return soup
        except Exception as e:
            logger.error(f"Error fetching page {url}: {e}")
            return None

    async def _fetch_listing_with_scroll(self, url: str) -> BeautifulSoup | None:
        """Render the category listing and scroll until all lazy products are loaded."""
        browser = await self._get_browser()
        # Square Online only hydrates the product grid at desktop-sized viewports.
        page = await browser.new_page(viewport={"width": 1440, "height": 900})

        try:
            await page.set_extra_http_headers(
                {
                    "User-Agent": BROWSER_USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                }
            )
            response = await page.goto(url, timeout=self.timeout * 1000, wait_until="domcontentloaded")
            if not response or not response.ok:
                raise Exception(f"Failed to load page: {response.status if response else 'No response'}")

            try:
                await page.wait_for_selector('a[href*="/product/"]', timeout=30000)
            except Exception:
                logger.warning(f"Timed out waiting for product links on {url}")
            await page.wait_for_timeout(3000)

            # Square Online paginates/infinite-scrolls the category grid; scroll until
            # the document height stabilises so the full in-stock catalogue is present.
            previous_height = 0
            for _ in range(25):
                await page.keyboard.press("End")
                await page.wait_for_timeout(2000)
                current_height = await page.evaluate("document.body.scrollHeight")
                if current_height == previous_height:
                    break
                previous_height = current_height

            html_content = await page.content()
            if self.session:
                self.session.requests_made += 1
            soup = BeautifulSoup(html_content, "lxml")
            if not soup.select('a[href*="/product/"]'):
                logger.warning(f"Listing render produced no product links for {url}")
                return None
            return soup

        finally:
            await page.close()

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract in-stock coffee product URLs from the Square Online listing.

        # Sold-out detection: Square Online hides out-of-stock items from the
        # category grid entirely, and any card that is still shown carries an
        # "Out of Stock" / "Sold out" label. We render the listing with Playwright
        # (scroll to load all), apply a card-level text check for those markers,
        # then run ``is_coffee_product_url``. Products missing from the listing are
        # handled by the out-of-stock diffjson path.
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        product_urls: list[str] = []
        seen: set[str] = set()

        for link in soup.select('a[href*="/product/"]'):
            href = link.get("href")
            if not href or not isinstance(href, str):
                continue
            full_url = self.resolve_url(href.split("?")[0].split("#")[0])

            # Card-level sold-out check: walk up to the nearest product card ancestor.
            card = link.find_parent(class_=_has_product_class)
            card_text = " ".join((card or link).get_text(" ", strip=True).split()).lower()
            if any(marker in card_text for marker in ("out of stock", "sold out", "unavailable")):
                logger.debug(f"Skipping sold-out product: {full_url}")
                continue

            if not self.is_coffee_product_url(full_url, required_path_patterns=["/product/"]):
                continue

            if full_url not in seen:
                seen.add(full_url)
                product_urls.append(full_url)

        # Exclude merch/equipment slugs (keep the roasters-choice sample box).
        excluded = [
            "grinder",
            "hoodie",
            "tees",
            "socks",
            "beanie",
            "tumbler",
            "scale",
            "brewer",
            "filters",
            "hats",
            "mural-tee",
        ]
        coffee_urls = [url for url in product_urls if not any(ex in url.lower() for ex in excluded)]

        logger.info(
            f"Found {len(coffee_urls)} in-stock coffee product URLs out of {len(product_urls)} from {store_url}"
        )
        return coffee_urls

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction on the rendered detail pages."""
        if not product_urls:
            return []

        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=True,
            use_optimized_mode=False,
            translate_to_english=False,
        )

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Pin USD — the registry default-currency lookup falls back to GBP for hyphenated names."""
        bean.currency = "USD"
        return bean
