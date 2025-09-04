"""Uncle Ben's Coffee scraper implementation with AI-powered extraction and screenshot support."""

import logging

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="uncle-ben",
    display_name="Uncle Ben's Coffee",
    roaster_name="Uncle Ben's Coffee",
    website="https://unclebencoffee.com",
    description="Specialty coffee roaster based in Hong Kong",
    requires_api_key=True,
    currency="HKD",
    country="Hong Kong",
    status="available",
)
class UncleBenCoffeeScraper(BaseScraper):
    """Scraper for Uncle Ben's Coffee with AI-powered extraction and screenshot support."""

    def __init__(self, api_key: str | None = None):
        """Initialize Uncle Ben's Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Uncle Ben's Coffee",
            base_url="https://unclebencoffee.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape, including pagination.

        Returns:
            List containing all coffee collection page URLs with pagination
        """
        # Start with the base collection URL to discover pagination
        base_urls = []

        # Add the first few pages - we'll discover the total number during scraping
        for page in range(1, 4):  # Start with reasonable range, will be refined during scraping
            page_url = f"https://unclebencoffee.com/collections/all-coffee-beans?page={page}"
            base_urls.append(page_url)

        return base_urls

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Uncle Ben's Coffee store using AI extraction.

        Returns:
            List of CoffeeBean objects
        """
        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=self._extract_product_urls_with_pagination,
            ai_extractor=self.ai_extractor,
            use_playwright=True,  # Use Playwright for screenshot support
        )

    async def take_screenshot(self, url: str, full_page: bool = True) -> bytes | None:
        """Take a screenshot focused on the product-info element.

        Overrides the base class method to capture the specific product-info element
        as requested in the requirements.

        Args:
            url: URL to take screenshot of
            full_page: Ignored for this implementation - we focus on product-info

        Returns:
            Screenshot bytes of the product-info element, or None if failed
        """
        try:
            # Use Playwright to navigate to the page and take targeted screenshot
            if not self._browser:
                from playwright.async_api import async_playwright

                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(headless=True)

            page = await self._browser.new_page()

            # Set viewport for consistent screenshots
            await page.set_viewport_size({"width": 1200, "height": 800})

            # Navigate to the product page
            await page.goto(url, wait_until="networkidle")

            # Wait for the product-info element to be present
            try:
                await page.wait_for_selector("product-info", timeout=10000)

                # Take a screenshot of just the product-info element
                element = page.locator("product-info")
                screenshot_bytes = await element.screenshot(type="png")

                await page.close()
                return screenshot_bytes

            except Exception as e:
                logger.warning(f"Could not find product-info element on {url}, taking full page screenshot: {e}")
                # Fallback to full page screenshot
                screenshot_bytes = await page.screenshot(type="png", full_page=True)
                await page.close()
                return screenshot_bytes

        except Exception as e:
            logger.error(f"Failed to take screenshot of {url}: {e}")
            if "page" in locals():
                await page.close()
            return None

    async def _extract_product_urls_with_pagination(self, store_url: str) -> list[str]:
        """Extract product URLs with automatic pagination detection.

        Args:
            store_url: URL of a collection page (may include pagination)

        Returns:
            List of product URLs for coffee products from this page
        """
        product_urls = []

        try:
            # Use Playwright to fetch the page for JavaScript-rendered content
            soup = await self.fetch_page(store_url, use_playwright=True)

            if not soup:
                logger.error(f"Failed to fetch store page: {store_url}")
                return []

            # Check if this page has products (for pagination boundary detection)
            has_products = self._has_products_on_page(soup)
            if not has_products:
                logger.info(f"No products found on page: {store_url}")
                return []

            # Extract product URLs using various selectors
            selectors = [
                # Shopify common selectors
                'a[href*="/products/"]',  # Any link to products
                ".product-item a",  # Product item containers
                ".product-card a",  # Product card containers
                ".grid-product__link",  # Grid product links
                ".product-link",  # Generic product links
                ".card-wrapper a",  # Card wrapper links
                "a.product-item-link",  # Product item links
            ]

            # Extract links using BeautifulSoup selectors
            for selector in selectors:
                try:
                    links = soup.select(selector)
                    for link in links:
                        if isinstance(link, Tag):
                            href = link.get("href", "")
                            if href and isinstance(href, str):
                                full_url = self.resolve_url(href)
                                if self._is_coffee_product_url(full_url):
                                    product_urls.append(full_url)
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")

            # Fallback: look for all product links in the HTML
            if not product_urls:
                all_links = soup.find_all("a", href=True)
                for link in all_links:
                    if isinstance(link, Tag):
                        href = link.get("href", "")
                        if href and isinstance(href, str) and "/products/" in href:
                            full_url = self.resolve_url(href)
                            if self._is_coffee_product_url(full_url):
                                product_urls.append(full_url)

        except Exception as e:
            logger.error(f"Error extracting URLs from {store_url}: {e}")

        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in product_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        logger.info(f"Found {len(unique_urls)} product URLs on {store_url}")
        return unique_urls

    def _has_products_on_page(self, soup: BeautifulSoup) -> bool:
        """Check if the page contains any products (for pagination boundary detection).

        Args:
            soup: BeautifulSoup object of the page

        Returns:
            True if products are found, False otherwise
        """
        # Look for common product indicators
        product_indicators = [
            'a[href*="/products/"]',
            ".product-item",
            ".product-card",
            ".grid-product",
            ".card-wrapper",
        ]

        for indicator in product_indicators:
            if soup.select(indicator):
                return True

        return False

    def _is_coffee_product_url(self, url: str) -> bool:
        """Filter URLs to include only coffee products.

        Args:
            url: Product URL to check

        Returns:
            True if URL appears to be for a coffee product
        """
        # Use base class method with coffee-specific patterns
        if not self.is_coffee_product_url(url, ["/products/"]):
            return False

        # Additional filtering for Uncle Ben's specific non-coffee items
        excluded_patterns = [
            "gift-card",
            "subscription",
            "equipment",
            "grinder",
            "brewing",
            "merchandise",
            "merch",
            "accessories",
            "cup",
            "mug",
            "filter",
            "apparel",
            "clothing",
        ]

        url_lower = url.lower()
        return not any(pattern in url_lower for pattern in excluded_patterns)
