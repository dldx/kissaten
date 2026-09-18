"""Cofmos Coffee Roasters scraper implementation with AI-powered extraction.

Cofmos is a Lithuanian specialty coffee roaster (cofmos.lt) running WordPress +
WooCommerce behind a Cloudflare managed challenge that blocks plain HTTP
clients (403 + "Just a moment..."). A headless Chromium can pass the challenge,
but the solve is intermittent: each navigation may re-challenge and the
Turnstile widget needs several seconds (sometimes retries) to clear. Therefore
this scraper:

1. overrides ``_fetch_with_playwright`` to wait (and retry) until the challenge
   page is replaced by the real page, following the ``flames_coffee.py`` model;
2. uses Playwright for every fetch (listing and product pages);
3. discovers products from the ``/kava/`` (coffee) WooCommerce category listing
   with ``sold-out`` badge class detection;
4. narrows product detail pages to ``main.site-main``.
"""

import asyncio
import logging

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="cofmos",
    display_name="Cofmos",
    roaster_name="Cofmos",
    website="https://cofmos.lt",
    description=(
        "Lithuanian specialty coffee roaster (Cofmos Coffee Roasters) offering "
        "freshly roasted single-origin beans and espresso blends."
    ),
    requires_api_key=True,
    currency="EUR",
    country="Lithuania",
    status="experimental",
)
class CofmosScraper(BaseScraper):
    """Scraper for Cofmos (cofmos.lt) with AI extraction behind Cloudflare."""

    def __init__(self, api_key: str | None = None):
        """Initialize Cofmos scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Cofmos",
            base_url="https://cofmos.lt",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=45.0,
        )

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get the coffee category listing URL (Lithuanian: 'kava' = coffee)."""
        return ["https://cofmos.lt/kava/"]

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction (Playwright, translated).

        Args:
            product_urls: List of URLs for new products

        Returns:
            List of newly scraped CoffeeBean objects
        """
        if not product_urls:
            return []

        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=True,  # Cloudflare challenge requires a real browser
            use_optimized_mode=False,
            translate_to_english=True,  # Lithuanian storefront — translate to English
        )

    async def _fetch_with_playwright(self, url: str) -> str:
        """Fetch page content using Playwright, waiting out the Cloudflare challenge.

        The site serves a Cloudflare managed challenge ("Just a moment...") on
        navigation. The challenge usually auto-solves within a few seconds and
        the page reloads; occasionally it re-challenges the next navigation and
        needs a fresh attempt. We poll the page title after each navigation and
        retry the whole navigation a few times before giving up.

        Args:
            url: URL to fetch

        Returns:
            Full HTML page content after the challenge has been cleared

        Raises:
            Exception: If the challenge cannot be cleared after all attempts.
        """
        browser = await self._get_browser()
        page = await browser.new_page()
        max_attempts = 4

        try:
            await page.set_extra_http_headers(self.headers)

            for attempt in range(1, max_attempts + 1):
                response = await page.goto(url, timeout=self.timeout * 1000, wait_until="domcontentloaded")
                if response and not response.ok and response.status != 403:
                    raise Exception(f"Failed to load page: {response.status}")

                # Poll until the challenge page is gone (it auto-reloads on solve)
                waited = 0
                max_wait = 30  # seconds per attempt
                while waited < max_wait:
                    title = await page.title()
                    if "Just a moment" not in title:
                        content = await page.content()
                        if waited:
                            logger.debug(f"Cloudflare challenge cleared after ~{waited}s for {url}")
                        return content
                    await asyncio.sleep(2)
                    waited += 2

                logger.warning(
                    f"Cloudflare challenge not cleared after {max_wait}s (attempt {attempt}/{max_attempts}) for {url}"
                )

            raise Exception(f"Cloudflare challenge could not be cleared for {url}")

        finally:
            await page.close()

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page (always via Playwright) and narrow product detail pages.

        The WooCommerce theme renders the full product UI (summary,
        description, attributes) inside ``main.site-main``. Narrowing to it
        strips nav, footer, scripts and unrelated markup before the HTML is
        sent to the AI extractor.

        Args:
            *args: Positional arguments forwarded to the base fetch_page.
            **kwargs: Keyword arguments forwarded to the base fetch_page.

        Returns:
            BeautifulSoup object (narrowed for product pages) or None if fetch failed.
        """
        try:
            kwargs["use_playwright"] = True
            soup = await super().fetch_page(*args, **kwargs)
            url = kwargs.get("url")
            if not url and len(args) > 0:
                url = args[0]
            # Only narrow product detail pages, leave listing pages untouched
            if "/produktai/" not in (url or ""):
                return soup
            if soup is None:
                return None
            main_el = soup.select("main.site-main")
            if len(main_el) == 1:
                logger.debug(f"Narrowed soup to main.site-main for {url}")
                return main_el[0]
            logger.warning(f"Expected 1 main.site-main for {url}, found {len(main_el)}")
            return soup
        except Exception as e:
            logger.error(f"Error fetching page {url if 'url' in dir() else '?'}: {e}")
            return None

    # Sold-out detection: WooCommerce class detection on the product card.
    # Cofmos's theme marks sold-out products with a "sold-out woocommerce-badge"
    # element (Lithuanian text "Nebėra" = "none left") inside the li.product
    # card. We skip any card containing that badge before applying
    # is_coffee_product_url filtering, so excluded products don't leak past
    # the stock check.
    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract in-stock product URLs from the /kava/ category listing.

        Args:
            store_url: URL of the coffee category page

        Returns:
            List of in-stock product URLs
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        product_urls: list[str] = []
        seen: set[str] = set()

        for card in soup.select("li.product"):
            link = card.select_one('a[href*="/produktai/"]')
            if not link:
                continue
            href = link.get("href")
            if not href or not isinstance(href, str):
                continue

            # Skip sold-out products before URL-pattern filtering
            if card.select_one(".sold-out") or card.select_one(".outofstock"):
                logger.debug(f"Skipping sold-out product: {href}")
                continue

            full_url = self.resolve_url(href.split("?")[0].split("#")[0])
            if full_url in seen:
                continue
            seen.add(full_url)
            product_urls.append(full_url)

        # Exclude brewing equipment / accessories (AeroPress, Hario V60,
        # Chemex, grinders, kettles, scales, filters). Coffee products —
        # including the Fermentation Project kit — are kept.
        coffee_urls = [
            url for url in product_urls if self.is_coffee_product_url(url, required_path_patterns=["/produktai/"])
        ]
        logger.info(f"Found {len(coffee_urls)} in-stock product URLs from {store_url}")
        return coffee_urls

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Force the currency to EUR.

        The WooCommerce product pages have no og:price:currency meta tag, so
        the base class currency detection never fires and default_currency
        falls back to GBP. Cofmos sells in euros.

        Args:
            bean: Extracted CoffeeBean object

        Returns:
            The bean with currency forced to EUR
        """
        bean.currency = "EUR"
        for option in bean.price_options or []:
            option.currency = "EUR"
        return bean
