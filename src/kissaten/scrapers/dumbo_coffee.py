"""Dumbo Coffee scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="dumbo",
    display_name="Dumbo Coffee",
    roaster_name="Coffee Dumbo",
    website="coffeedumbo.tw",
    description="Taiwan-based specialty coffee roaster with Chinese and English options",
    requires_api_key=True,
    currency="GBP",  # They use GBP on their site
    country="Taiwan",
    status="available",
)
class DumboCoffeeScraper(BaseScraper):
    """Scraper for Dumbo Coffee (coffeedumbo.tw) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Dumbo Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Coffee Dumbo",
            base_url="https://www.coffeedumbo.tw",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the store URL for coffee beans
        """
        return ["https://www.coffeedumbo.tw/categories/%E5%92%96%E5%95%A1%E8%B1%86?limit=72"]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Dumbo Coffee store using AI extraction with screenshot support.

        Returns:
            List of CoffeeBean objects
        """
        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=self._extract_product_urls_from_store,
            ai_extractor=self.ai_extractor,
            use_playwright=True,  # Use Playwright for screenshot support
            batch_size=2,  # Conservative batch size for screenshot processing
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

        # Custom selectors for Dumbo Coffee
        # Looking for product links in the coffee beans category page
        custom_selectors = [
            'a[href*="/products/"]',
            ".product-card a",
            ".product-item a",
            ".product-link",
        ]

        return self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/products/"],
            selectors=custom_selectors,
        )

    async def take_screenshot(self, url: str, full_page: bool = True) -> bytes | None:
        """Take a screenshot focused on the ProductDetail-product row element.

        Overrides the base class method to capture the specific ProductDetail-product row element
        as requested in the requirements.

        Args:
            url: URL to take screenshot of
            full_page: Ignored for this implementation - we focus on ProductDetail-product row

        Returns:
            Screenshot bytes of the ProductDetail-product row element, or None if failed
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

            # Wait for the ProductDetail-product row element to be present
            try:
                await page.wait_for_selector(".ProductDetail-product.row", timeout=10000)

                # Take a screenshot of just the ProductDetail-product row element
                element = page.locator(".ProductDetail-product.row")
                screenshot_bytes = await element.screenshot(type="png")

                await page.close()
                return screenshot_bytes

            except Exception as e:
                logger.warning(
                    f"Could not find ProductDetail-product row element on {url}, taking full page screenshot: {e}"
                )
                # Fallback to full page screenshot
                screenshot_bytes = await page.screenshot(type="png", full_page=True)
                await page.close()
                return screenshot_bytes

        except Exception as e:
            logger.error(f"Failed to take screenshot of {url}: {e}")
            if "page" in locals():
                await page.close()
            return None

    async def _extract_bean_with_ai(
        self, ai_extractor, soup, product_url: str, use_optimized_mode: bool = False
    ) -> CoffeeBean | None:
        """Extract coffee bean data using AI with screenshot support, focusing on ProductDetail-product row selector.

        Args:
            ai_extractor: AI extractor instance
            soup: BeautifulSoup object of the product page
            product_url: URL of the product page
            use_optimized_mode: Whether to use optimized mode (with screenshots)

        Returns:
            CoffeeBean object or None if extraction fails
        """
        # Find the specific ProductDetail-product row div as requested
        product_detail = soup.find("div", class_="ProductDetail-product row")

        if product_detail:
            # Use only the relevant product section for AI extraction
            html_content = str(product_detail)
            logger.debug(f"Using ProductDetail-product row content for {product_url}")
        else:
            # Fallback to full page if the specific selector isn't found
            html_content = str(soup)
            logger.debug(f"ProductDetail-product row not found for {product_url}, using full page")

        # Use the base class extraction logic which handles screenshots automatically
        if use_optimized_mode:
            # Take a screenshot focusing on the ProductDetail-product row
            screenshot_bytes = await self.take_screenshot(product_url)
            bean = await ai_extractor.extract_coffee_data(
                html_content, product_url, screenshot_bytes, use_optimized_mode=True
            )
        else:
            # Standard mode without screenshots
            bean = await ai_extractor.extract_coffee_data(html_content, product_url)

        if bean:
            # Ensure correct roaster details
            bean.roaster = "Coffee Dumbo"
            bean.currency = "GBP"
            return bean

        return None
