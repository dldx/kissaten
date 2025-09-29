"""One Half Coffee scraper implementation with AI-powered extraction."""

import asyncio
import logging

from bs4 import BeautifulSoup

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="one-half-coffee",
    display_name="One Half Coffee",
    roaster_name="One Half Coffee",
    website="https://www.onehalfcoffee.com",
    description="Malaysian specialty coffee roaster based in Petaling Jaya, offering single-origin "
    "filter coffees, espresso blends, and collaboration coffees with detailed flavor profiling",
    requires_api_key=True,
    currency="MYR",
    country="Malaysia",
    status="available",
)
class OneHalfCoffeeScraper(BaseScraper):
    """Scraper for One Half Coffee (onehalfcoffee.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize One Half Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="One Half Coffee",
            base_url="https://www.onehalfcoffee.com",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def fetch_page(self, url: str, retries: int = 0, use_playwright: bool = False) -> BeautifulSoup | None:
        """Override fetch_page to handle infinite scroll loading on One Half Coffee.

        Args:
            url: URL to fetch
            retries: Number of retries attempted
            use_playwright: Whether to use Playwright instead of httpx

        Returns:
            BeautifulSoup object or None if failed
        """
        # For store pages, we need to use Playwright to handle infinite scroll
        if any(store_path in url for store_path in ["/store/", "/collections/"]):
            use_playwright = True

        if not use_playwright:
            # For product pages, use the base implementation
            return await super().fetch_page(url, retries, use_playwright)

        # Custom Playwright implementation with infinite scroll
        try:
            # Rate limiting
            if retries == 0:
                await asyncio.sleep(self.rate_limit_delay)

            browser = await self._get_browser()
            page = await browser.new_page()

            try:
                # Set user agent and other headers
                await page.set_extra_http_headers(self.headers)

                # Navigate to the page
                response = await page.goto(url, timeout=self.timeout * 1000, wait_until="domcontentloaded")

                if not response or not response.ok:
                    logger.error(f"Failed to load page: {response.status if response else 'No response'}")
                    return None

                # Wait for initial content to load
                await page.wait_for_timeout(3000)

                # Auto scroll to load all products (similar to JavaScript example)
                scroll_attempts = await self._auto_scroll(page)

                logger.info(f"Completed scrolling after {scroll_attempts} attempts for {url}")

                # Get the final page content
                html_content = await page.content()

                # Track requests
                if self.session:
                    self.session.requests_made += 1

                # Parse HTML
                soup = BeautifulSoup(html_content, "lxml")
                logger.debug(f"Successfully fetched with infinite scroll: {url}")
                return soup

            finally:
                await page.close()

        except Exception as e:
            logger.error(f"Error fetching page with infinite scroll {url}: {e}")
            if self.session:
                self.session.add_error(f"Fetch error for {url}: {e}")

            # Retry logic
            if retries < self.max_retries:
                logger.info(f"Retrying {url} (attempt {retries + 1}/{self.max_retries})")
                await asyncio.sleep(2**retries)  # Exponential backoff
                return await self.fetch_page(url, retries + 1, use_playwright)

        return None

    async def _auto_scroll(self, page) -> int:
        """Auto scroll function similar to the JavaScript example.

        Args:
            page: Playwright page object

        Returns:
            Number of scroll attempts made
        """
        max_scrolls = 100
        scroll_delay = 4000  # 4 seconds
        previous_height = 0
        scroll_attempts = 0

        while scroll_attempts < max_scrolls:
            # Press End key to scroll to bottom (similar to page.keyboard.down('End'))
            await page.keyboard.press('End')
            await page.wait_for_timeout(scroll_delay)

            # Get current scroll height
            current_height = await page.evaluate("document.body.scrollHeight")

            # If height hasn't changed, we've reached the end
            if current_height == previous_height:
                logger.debug(f"No new content loaded after {scroll_attempts} scroll attempts")
                break

            previous_height = current_height
            scroll_attempts += 1

            # Optional: Look for and click "Load more" button if present
            try:
                load_more_button = await page.wait_for_selector(
                    'button:has-text("Load more"), button:has-text("Show more"), .load-more',
                    timeout=1000
                )
                if load_more_button:
                    await load_more_button.click()
                    await page.wait_for_timeout(2000)
                    logger.debug("Clicked load more button")
            except Exception:
                # No load more button found, continue scrolling
                pass

        return scroll_attempts

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the coffee collection URLs
        """
        return [
            "https://www.onehalfcoffee.com/store/filter-coffee",
            "https://www.onehalfcoffee.com/store/espresso-coffee",
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

        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=False,
        )

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from store page.

        Args:
            store_url: URL of the store page

        Returns:
            List of product URLs
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        # Get all product URLs using the base class method
        product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/products/"],
            selectors=[
                # Generic product link selectors
                'a[href*="/products/"]',
                '.product-item a',
                '.product-link',
                '.product-card a',
                '.product a',
                # One Half Coffee specific selectors
                'a[href*="/products/"]',
                'h3 a',  # Product title links
                'h4 a',  # Alternative title links
            ],
        )

        # Filter out non-coffee products (subscriptions, equipment, drip bags, etc.)
        excluded_products = [
            "subscription",  # Subscription products
            "dripper",  # Coffee drippers
            "equipment",  # Coffee equipment
            "accessory",  # Accessories
            "server",  # Coffee servers
            "holder",  # Dripper holders
            "sieve",  # Grind sieves
            "water",  # Brewing water
            "drip-bag",  # Drip bag coffee
            "dip-bag",  # Drip bag coffee (alternative spelling)
            "gift-card",  # Gift cards
            "gift",  # General gift items
            "bundle",  # Product bundles/sets
            "set",  # Product sets
            "duo-set",  # Duo sets
        ]

        filtered_urls = []
        for url in product_urls:
            if url and isinstance(url, str):
                url_lower = url.lower()
                if not any(excluded in url_lower for excluded in excluded_products):
                    filtered_urls.append(url)

        return filtered_urls
