"""Cupping Room scraper implementation with AI-powered extraction.

Cupping Room (cuppingroom.hk) is a Hong Kong specialty coffee roasting
company. The storefront is a fully client-rendered React SPA backed by the
`gols.com.hk` e-commerce API, so every page (listing + product) must be
rendered with a headless browser before anything useful is in the DOM — a
plain httpx GET only returns the empty ``#root`` shell.

The product listing is organised by category; the coffee beans live under
the "Beans" primary category (id 115), which already contains the Blend and
Single Origin sub-category products. We target that single category page so
we never pull capsules, drip bags, accessories or credit packs (which have
numeric URLs and cannot be filtered out by URL keywords).

Product detail pages render rich, English text (name, price in HKD, origin,
process, tasting notes, description), so standard AI extraction works well
and no translation is required.
"""

import asyncio
import logging

from bs4 import BeautifulSoup

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="cupping-room",
    display_name="Cupping Room",
    roaster_name="Cupping Room",
    website="https://cuppingroom.hk/",
    description="Hong Kong specialty coffee roasting company offering single-origin "
    "filter coffees and espresso blends with detailed origin and flavour profiling",
    requires_api_key=True,
    currency="HKD",
    country="Hong Kong",
    status="available",
)
class CuppingRoomScraper(BaseScraper):
    """Scraper for Cupping Room (cuppingroom.hk) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Cupping Room scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Cupping Room",
            base_url="https://cuppingroom.hk/",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=45.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def _get_excluded_url_patterns(self) -> list[str]:
        """Excluded URL patterns for Cupping Room.

        The base class rejects URLs containing "cupping" (to skip cupping-session
        tickets), but every product URL here is under ``cuppingroom.hk`` — the
        roaster's own domain — so that generic exclusion would reject the entire
        catalogue. We drop just that one keyword.
        """
        return [p for p in super()._get_excluded_url_patterns() if p != "cupping"]

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Enforce the store currency for every extracted bean.

        Cupping Room is a mono-currency (HKD) storefront. The rendered product
        pages expose no ``og:price:currency`` meta tag, so the auto-detector
        cannot confirm HKD and the AI occasionally falls back to GBP. We pin the
        currency to the roaster's registered default (HKD) for correctness.

        Args:
            bean: The extracted CoffeeBean

        Returns:
            The bean with currency set, or None
        """
        bean.currency = "HKD"
        return bean

    async def _scroll_to_load(self, page) -> None:
        """Scroll the page to trigger any lazy-loaded content.

        Args:
            page: Playwright page object
        """
        try:
            previous_height = 0
            for _ in range(20):
                await page.keyboard.press("End")
                await page.wait_for_timeout(1500)
                current_height = await page.evaluate("document.body.scrollHeight")
                if current_height == previous_height:
                    break
                previous_height = current_height
        except Exception as e:  # pragma: no cover - best-effort scroll
            logger.debug(f"Scroll ended early for page: {e}")

    async def fetch_page(self, url: str, retries: int = 0, use_playwright: bool = False) -> BeautifulSoup | None:
        """Fetch and render a Cupping Room page with a headless browser.

        The site is a fully client-rendered React SPA, so every page must be
        rendered (store + product). We wait for the app to hydrate and scroll
        the listing to trigger any lazy-loaded products.

        Args:
            url: URL to fetch
            retries: Number of retries attempted
            use_playwright: Unused - this scraper always renders with Playwright

        Returns:
            BeautifulSoup object or None if failed
        """
        if retries == 0:
            await asyncio.sleep(self.rate_limit_delay)

        browser = await self._get_browser()
        page = await browser.new_page()

        try:
            await page.set_extra_http_headers(self.headers)

            response = await page.goto(url, timeout=self.timeout * 1000, wait_until="domcontentloaded")
            if not response or not response.ok:
                raise Exception(f"Failed to load page: {response.status if response else 'No response'}")

            # Give the React app time to fetch data and hydrate the DOM.
            await page.wait_for_timeout(5000)

            # Scroll listing pages to trigger lazy loading.
            await self._scroll_to_load(page)

            html_content = await page.content()

            if self.session:
                self.session.requests_made += 1

            soup = BeautifulSoup(html_content, "lxml")
            logger.debug(f"Successfully fetched (playwright): {url}")
            return soup

        except Exception as e:
            logger.warning(f"Playwright fetch failed for {url}: {e}")
            if self.session:
                self.session.add_error(f"Playwright fetch error: {url} - {e}")

            if retries < self.max_retries:
                logger.info(f"Retrying {url} (attempt {retries + 1}/{self.max_retries})")
                await asyncio.sleep(2**retries)  # Exponential backoff
                return await self.fetch_page(url, retries + 1, use_playwright)

        finally:
            await page.close()

        return None

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the coffee bean category URL. The "Beans" primary
            category (id 115) covers Blend and Single Origin products, so it is
            enough to capture every coffee bean without pulling capsules, drip
            bags, accessories or credit packs.
        """
        return [
            "https://cuppingroom.hk/shop/115",
        ]

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction.

        Args:
            product_urls: List of URLs for new products

        Returns:
            List of newly scraped CoffeeBean objects
        """
        if not product_urls:
            return []

        # Create a function that returns the product URLs for the AI extraction
        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=True,
            use_optimized_mode=False,
            translate_to_english=False,  # Cupping Room renders product pages in English
        )

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from the store page.

        The listing is rendered by React, so each product card is a
        ``div.product-wrap`` containing the product link(s). We check the card
        text for sold-out markers before accepting the link.

        Args:
            store_url: URL of the store page

        Returns:
            List of unique coffee product URLs
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        product_urls = []
        # Sold-out detection: text on the product card.
        sold_out_markers = ("sold out", "out of stock", "out-of-stock", "售罄", "缺貨")

        for card in soup.select("div.product-wrap"):
            card_text = card.get_text(" ", strip=True).lower()
            if any(marker in card_text for marker in sold_out_markers):
                logger.debug(f"Skipping sold-out product card: {card_text[:60]}")
                continue

            link = card.select_one('a[href*="/product/"]')
            if link is None:
                continue

            href = link.get("href")
            if not href:
                continue

            url = self.resolve_url(href)
            if self.is_coffee_product_url(url, required_path_patterns=["/product/"]):
                product_urls.append(url)

        # Remove duplicates while preserving order (each card repeats its link).
        return self.deduplicate_urls(product_urls)
