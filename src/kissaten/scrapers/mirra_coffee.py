"""Mirra Coffee scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="mirra-coffee",
    display_name="Mirra Coffee",
    roaster_name="Mirra Coffee",
    website="https://www.mirracoffee.com",
    description="The American Nordic Roastery specializing in hyper-local, "
    "single-producer lots with Nordic-style light roasting",
    requires_api_key=True,
    currency="USD",
    country="USA",
    status="available",
)
class MirraCoffeeScraper(BaseScraper):
    """Scraper for Mirra Coffee (mirracoffee.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Mirra Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Mirra Coffee",
            base_url="https://www.mirracoffee.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the coffee collection URL
        """
        return ["https://www.mirracoffee.com/coffee-1-eFYbt"]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Mirra Coffee using AI extraction.

        Returns:
            List of CoffeeBean objects
        """
        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=self._extract_product_urls_from_store,
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
            url_path_patterns=["/p/"],
            selectors=[
                # Generic product link selectors
                'a[href*="/p/"]',
                '.product-item a',
                '.product-link',
                '.product-card a',
                '.product a',
                # Mirra specific selectors based on observed URLs
                'a[href*="/coffee-1-eFYbt/p/"]',
                'h3 a',  # Product title links
                'h4 a',  # Alternative title links
            ],
        )

        # Filter out non-coffee products (subscriptions, gift cards, etc.)
        excluded_products = [
            "subscription",  # Subscription products
            "gift-card",  # Gift cards
            "gift",  # General gift items
            "wholesale",  # Wholesale products
        ]

        filtered_urls = []
        for url in product_urls:
            # Check if any excluded product identifier is in the URL
            if not any(excluded in url.lower() for excluded in excluded_products):
                filtered_urls.append(url)

        return filtered_urls

    async def take_screenshot(self, url: str, full_page: bool = True) -> bytes | None:
        """Take a screenshot of the product gallery image with aria-describedby="product-gallery-slides-item-2".

        This overrides the base class method to capture the specific product image
        that contains tasting notes and other detailed information.

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

            # Try to find the specific product gallery image
            try:
                # Look for the image with the specific aria-describedby attribute
                image_element = await page.wait_for_selector(
                    'img[aria-describedby="product-gallery-slides-item-2"]',
                    timeout=5000
                )

                if image_element:
                    # Take a screenshot of just this element
                    screenshot_bytes = await image_element.screenshot(type="png")
                    logger.debug(f"Successfully took screenshot of product gallery image from: {url}")
                    return screenshot_bytes
                else:
                    logger.warning(
                        f"Could not find product gallery image with "
                        f"aria-describedby='product-gallery-slides-item-2' on {url}"
                    )

            except Exception as e:
                logger.warning(f"Could not find specific product gallery image on {url}: {e}")

            # Fallback: try other common product image selectors
            fallback_selectors = [
                'img[aria-describedby*="product-gallery"]',  # Any product gallery image
                '.product-gallery img',  # Images in product gallery
                '.product-images img',   # Images in product images container
                '.product-image img',    # Images in product image container
                '[data-hook="product-image"] img',  # Wix-style product images
            ]

            for selector in fallback_selectors:
                try:
                    image_element = await page.wait_for_selector(selector, timeout=2000)
                    if image_element:
                        screenshot_bytes = await image_element.screenshot(type="png")
                        logger.debug(f"Successfully took fallback screenshot using selector '{selector}' from: {url}")
                        return screenshot_bytes
                except Exception:
                    continue

            # Final fallback: take a screenshot of the main product area
            try:
                product_area = await page.wait_for_selector(
                    '.product, .product-details, .product-page, [data-hook="product"]',
                    timeout=2000
                )
                if product_area:
                    screenshot_bytes = await product_area.screenshot(type="png")
                    logger.debug(f"Successfully took product area screenshot from: {url}")
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
