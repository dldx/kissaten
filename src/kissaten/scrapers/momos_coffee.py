"""Momos Coffee scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="momos-coffee",
    display_name="Momos Coffee",
    roaster_name="Momos Coffee",
    website="https://en.momos.co.kr",
    description="Korean specialty coffee roaster from Busan, offering signature blends, "
    "seasonal blends, single estate coffees, and Havana collection",
    requires_api_key=True,
    currency="USD",
    country="South Korea",
    status="available",
)
class MomosCoffeeScraper(BaseScraper):
    """Scraper for Momos Coffee (en.momos.co.kr) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Momos Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Momos Coffee",
            base_url="https://en.momos.co.kr",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the coffee collection URLs
        """
        return [
            "https://en.momos.co.kr/custom/sub/product_category/rb_signature.html?cate_no=44&page=1",
            "https://en.momos.co.kr/custom/sub/product_category/rb_seasonal.html?cate_no=138",
            "https://en.momos.co.kr/custom/sub/product_category/rb_single.html?cate_no=45",
            "https://en.momos.co.kr/custom/sub/product_category/rb_havana.html?cate_no=139"
        ]

    async def scrape(self, force_full_update: bool = False) -> list[CoffeeBean]:
        """Scrape coffee beans from Momos Coffee with efficient stock updates.

        This method will check for existing beans and create diffjson stock updates
        for products that already have bean files, or do full scraping for new products.

        Args:
            force_full_update: If True, perform full scraping for all products instead of diffjson updates

        Returns:
            List of CoffeeBean objects (only new products, or all products if force_full_update=True)
        """
        self.start_session()
        from pathlib import Path

        output_dir = Path("data")

        all_product_urls = []
        for store_url in self.get_store_urls():
            product_urls = await self._extract_product_urls_from_store(store_url)
            all_product_urls.extend(product_urls)

        if force_full_update:
            logger.info(
                f"Force full update enabled - performing full scraping for all {len(all_product_urls)} products"
            )
            return await self._scrape_new_products(all_product_urls)

        in_stock_count, out_of_stock_count = await self.create_diffjson_stock_updates(
            all_product_urls, output_dir, force_full_update
        )

        new_urls = []
        for url in all_product_urls:
            if not self._is_bean_already_scraped_anywhere(url):
                new_urls.append(url)

        logger.info(f"Found {in_stock_count} existing products for stock updates")
        logger.info(f"Found {out_of_stock_count} products now out of stock")
        logger.info(f"Found {len(new_urls)} new products for full scraping")

        if new_urls:
            return await self._scrape_new_products(new_urls)

        return []

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
            use_optimized_mode=True,
            translate_to_english=True,
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
        product_urls = [
            f"https://en.momos.co.kr{href}"
            for a in soup.select('a[href*="/product/"]')
            if (href := a.get("href")) and isinstance(href, str)
        ]
        product_urls = list(set(product_urls))  # Remove duplicates

        # Filter out non-coffee products (subscriptions, accessories, etc.)
        excluded_products = [
            "subscription",  # Subscription products
            "gift-card",  # Gift cards
            "gift",  # General gift items
            "wholesale",  # Wholesale products
            "equipment",  # Coffee equipment
            "accessory",  # Accessories
            "merchandise",  # Merchandise
            "search.html"  # Search or non-product pages
        ]

        filtered_urls = []
        for url in product_urls:
            if url and isinstance(url, str) and not any(excluded in url.lower() for excluded in excluded_products):
                filtered_urls.append(url)

        return filtered_urls

    async def take_screenshot_(self, url: str, full_page: bool = True) -> bytes | None:
        """Take a screenshot of the div with classes "accessories product" or "accessories model".

        This overrides the base class method to capture the specific product image
        that contains detailed product information and tasting notes.

        Args:
            url: URL to take screenshot of
            full_page: Whether to take a full page screenshot or just viewport (ignored for this implementation)

        Returns:
            Screenshot as bytes or None if failed
        """
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

            # Wait for dynamic content to load
            await page.wait_for_timeout(3000)

            # Try to find the specific div with "accessories product" classes
            try:
                # Look for div with both "accessories" and "product" classes
                accessories_element = await page.wait_for_selector(
                    'div.accessories.product',
                    timeout=5000
                )

                if accessories_element:
                    # Take a screenshot of just this element
                    screenshot_bytes = await accessories_element.screenshot(type="png")
                    logger.debug(f"Successfully took screenshot of accessories product div from: {url}")
                    return screenshot_bytes

            except Exception as e:
                logger.warning(f"Could not find div with 'accessories product' classes on {url}: {e}")

            # Try alternative: div with "accessories model" classes
            try:
                accessories_model_element = await page.wait_for_selector(
                    'div.accessories.model',
                    timeout=3000
                )

                if accessories_model_element:
                    # Take a screenshot of just this element
                    screenshot_bytes = await accessories_model_element.screenshot(type="png")
                    logger.debug(f"Successfully took screenshot of accessories model div from: {url}")
                    return screenshot_bytes

            except Exception as e:
                logger.warning(f"Could not find div with 'accessories model' classes on {url}: {e}")

            # Fallback: try other common product image/detail selectors
            fallback_selectors = [
                'div[class*="accessories"]',  # Any div with accessories in class
                'div[class*="product"]',      # Any div with product in class
                '.product-details',           # Product details container
                '.product-images',            # Product images container
                '.product-info',              # Product info container
                '.product-gallery',           # Product gallery
                'img[class*="accessories"]',  # Images with accessories class
                'img[class*="product"]',      # Images with product class
            ]

            for selector in fallback_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=2000)
                    if element:
                        screenshot_bytes = await element.screenshot(type="png")
                        logger.debug(f"Successfully took fallback screenshot using selector '{selector}' from: {url}")
                        return screenshot_bytes
                except Exception:
                    continue

            # Final fallback: take a screenshot of the main content area
            try:
                main_content = await page.wait_for_selector(
                    'main, .main, .content, .product-page, #content',
                    timeout=2000
                )
                if main_content:
                    screenshot_bytes = await main_content.screenshot(type="png")
                    logger.debug(f"Successfully took main content screenshot from: {url}")
                    return screenshot_bytes
            except Exception:
                pass

            # Ultimate fallback: full page screenshot
            screenshot_bytes = await page.screenshot(full_page=True, type="png")
            logger.debug(f"Took full page screenshot as final fallback from: {url}")
            return screenshot_bytes

        except Exception as e:
            logger.error(f"Failed to take screenshot of {url}: {e}")
            return None

        finally:
            await page.close()
