"""Glitch Coffee scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="glitch",
    display_name="Glitch Coffee",
    roaster_name="Glitch Coffee & Roasters",
    website="https://shop.glitchcoffee.com",
    description="Specialty coffee roasters from Japan with unique processing methods",
    requires_api_key=True,
    currency="JPY",
    country="Japan",
    status="available",
)
class GlitchCoffeeScraper(BaseScraper):
    """Scraper for Glitch Coffee (shop.glitchcoffee.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Glitch Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Glitch Coffee & Roasters",
            base_url="https://shop.glitchcoffee.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the main collection URLs with pagination
        """
        return [
            "https://shop.glitchcoffee.com/en/collections/all",
            "https://shop.glitchcoffee.com/en/collections/all?page=2",
            # Add more pages as needed - they show 32 products per page
        ]

    async def scrape(self, force_full_update: bool = False) -> list[CoffeeBean]:
        """Scrape coffee beans from Glitch Coffee with efficient stock updates.

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

        # Custom selectors for Glitch Coffee Shopify store
        custom_selectors = [
            'a[href*="/en/products/"]',
            ".product-item-link",
            ".product-link",
            "h3 > a",  # Product titles that are links
            ".grid-product__title a",  # Common Shopify pattern
        ]

        product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/en/products/"],
            selectors=custom_selectors,
        )

        # Filter out non-coffee products
        filtered_urls = []
        for url in product_urls:
            if self._is_coffee_product_url(url):
                filtered_urls.append(url)

        return filtered_urls

    def _is_coffee_product_url(self, url: str) -> bool:
        """Filter out non-coffee products by URL.

        Args:
            url: Product URL to check

        Returns:
            True if this appears to be a coffee product URL
        """
        # Exclude equipment, merchandise, and other non-coffee items
        excluded_patterns = [
            't-shirt',
            'tshirt',
            'shirt',
            'merchandise',
            'merch',
            'collaboration',
            'equipment',
            'accessories',
            'brewing',
            'kettle',
            'grinder',
            'subscription',
        ]

        url_lower = url.lower()
        return not any(pattern in url_lower for pattern in excluded_patterns)
