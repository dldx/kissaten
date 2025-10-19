"""Prolog coffee scraper implementation with AI-powered extraction."""

import asyncio
import logging

from bs4 import BeautifulSoup

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="prolog-coffee",
    display_name="Prolog Coffee",
    roaster_name="Prolog Coffee",
    website="https://www.prologcoffee.com",
    description="Specialty coffee roaster based in Copenhagen, Denmark",
    requires_api_key=True,
    currency="DKK",
    country="Denmark",
    status="available",
)
class PrologCoffeeScraper(BaseScraper):
    """Scraper for Prolog Coffee with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Prolog Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Prolog Coffee",
            base_url="https://www.prologcoffee.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the coffee category URL
        """
        return ["https://www.prologcoffee.com/collections/buy-our-coffee"]
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

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from store page.

        Args:
            store_url: URL of the store page

        Returns:
            List of product URLs
        """
        soup = await self.fetch_page(store_url, use_playwright=True)
        if not soup:
            return []

        # Extract all product URLs using the base class method
        all_product_url_el = soup.select('a.product-item__image-link[href*="/products/"]')
        all_product_urls = []
        for el in all_product_url_el:
            all_product_urls.append(el["href"])

        excluded_pattern = ["xmas", "voucher", "advent"]

        # Filter coffee products using base class method
        coffee_urls = []
        for url in all_product_urls:
            if self.is_coffee_product_url(url, required_path_patterns=["/products/"]) and not any(
                pattern in url for pattern in excluded_pattern
            ):
                coffee_urls.append(f"{self.base_url}{url}")

        logger.info(f"Found {len(coffee_urls)} coffee product URLs out of {len(all_product_urls)} total products")
        return coffee_urls
