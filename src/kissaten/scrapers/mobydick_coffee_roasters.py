"""Module Coffee scraper implementation with AI-powered extraction."""

import logging

from playwright.async_api import Page

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


@register_scraper(
    name="mobydick-coffee-roasters",
    display_name="MobyDick Coffee Roasters",
    roaster_name="MobyDick Coffee Roasters",
    website="https://mobydickcoffeeroasters.guide",
    description="Speciality coffee roaster based in Shanghai, China.",
    requires_api_key=True,
    currency="CNY",
    country="China",
    status="available",
)
class MobyDickCoffeeRoastersScraper(BaseScraper):
    """Scraper for MobyDick Coffee Roasters (mobydickcoffeeroasters.guide) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize MobyDick Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="MobyDick Coffee Roasters",
            base_url="https://mobydickcoffeeroasters.guide",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the coffee collection URL
        """
        return ["https://mobydickcoffeeroasters.guide/delicious"]


    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction.

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
            use_playwright=False,
            translate_to_english=True
        )

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        # No prices are displayed on the site, so we set price to None and currency to CNY
        bean.price = None
        bean.currency = "CNY"
        bean.price_options = []
        return bean

    async def fetch_product_urls_with_playwright(self, url: str) -> str:
        """Fetch page content using Playwright.
        Moby Dick is a little complicated. We need to trigger the folding of certain sections to reveal all products.

        Args:
            url: URL to fetch

        Returns:
            HTML content as string

        Raises:
            Exception: If fetch fails
        """
        browser = await self._get_browser()
        page: Page = await browser.new_page()

        try:
            # Set user agent and other headers
            await page.set_extra_http_headers(self.headers)

            # Navigate to the page
            response = await page.goto(url, timeout=self.timeout * 1000, wait_until="domcontentloaded")

            if not response or not response.ok:
                raise Exception(f"Failed to load page: {response.status if response else 'No response'}")

            # Wait a bit for dynamic content to load
            await page.wait_for_timeout(1000)

            # Trigger div.notion-toggle elements to reveal hidden products
            toggle_selectors = await page.query_selector_all("div.notion-toggle")

            for toggle in toggle_selectors:
                try:
                    await toggle.click()
                    await page.wait_for_timeout(500)  # Wait for content to reveal
                except Exception as e:
                    logger.warning(f"Failed to click toggle: {e}")
            # Get the page content
            content = await page.content()
            return content

        finally:
            await page.close()

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page and return its BeautifulSoup object.

        Args:
            url: URL of the page to fetch
            use_playwright: Whether to use Playwright for fetching

        Returns:
            BeautifulSoup object of the page, or None if fetch failed
        """
        try:
            soup = await super().fetch_page(*args, **kwargs)
            url = kwargs.get("url")
            if not url and len(args) > 0:
                url = args[0]
            if "/delicious/" not in (url or ""):
                return soup  # Only modify product pages
            # Find unnecessary notes section and delete it to avoid confusion with AI extraction
            notes_section = soup.select("div.notion-collection")
            for section in notes_section:
                section.decompose()
            return soup
        except Exception as e:
            logger.error(f"Error fetching page {url}: {e}")
            return None


    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from store page.

        Args:
            store_url: URL of the store page

        Returns:
            List of product URLs
        """
        soup = BeautifulSoup(await self.fetch_product_urls_with_playwright(store_url), "html.parser")
        if not soup:
            return []

        # Get all product URLs using the base class method
        product_urls_el = soup.select('a[href*="/delicious/"]')
        product_urls = [el.get("href") for el in product_urls_el]

        # Filter out excluded products
        excluded_products = ["gift-card", "tote-bag", "subscription"]

        filtered_urls = []
        for url in product_urls:
            if url and isinstance(url, str) and not any(excluded in url.lower() for excluded in excluded_products):
                filtered_urls.append(self.resolve_url(url ))

        return list(set(filtered_urls))
