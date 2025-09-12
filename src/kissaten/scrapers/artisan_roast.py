"""Scraper for Artisan Roast Chile coffee roaster.

Artisan Roast is a Chilean specialty coffee roaster focused on circular coffee practices.
They offer single origins and blends with Chilean Peso pricing.
"""

import logging
from pathlib import Path

from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="artisan-roast-cl",
    display_name="Artisan Roast Chile",
    roaster_name="Artisan Roast Chile",
    website="https://shop.artisanroast.cl",
    description="Chilean specialty coffee roaster focused on circular coffee practices",
    requires_api_key=True,  # Use AI extraction for this Spanish-language site
    currency="CLP",  # Chilean Peso
    country="Chile",
    status="available"
)
class ArtisanRoastScraper(BaseScraper):
    """Scraper for Artisan Roast Chile coffee roaster."""

    def __init__(self, api_key: str | None = None):
        super().__init__(
            roaster_name="Artisan Roast Chile",
            base_url="https://shop.artisanroast.cl",
            rate_limit_delay=1.0,
            max_retries=3,
            timeout=30.0
        )

        # Initialize AI extractor for this Spanish-language site
        self.ai_extractor = None
        try:
            from ..ai import CoffeeDataExtractor
            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
        except ImportError:
            logger.warning("AI extractor not available - falling back to traditional extraction")

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape."""
        return [
            "https://shop.artisanroast.cl/collections/origenes",  # Single origins
            "https://shop.artisanroast.cl/collections/blends",    # Blends
        ]

    async def scrape(self, force_full_update: bool = False) -> list[CoffeeBean]:
        """Scrape coffee beans from Artisan Roast Chile with efficient stock updates.

        This method will check for existing beans and create diffjson stock updates
        for products that already have bean files, or do full scraping for new products.

        Args:
            force_full_update: If True, perform full scraping for all products instead of diffjson updates

        Returns:
            List of CoffeeBean objects (only new products, or all products if force_full_update=True)
        """
        # Start session and get all current product URLs from the website
        self.start_session()
        output_dir = Path("data")

        all_product_urls = []
        for store_url in self.get_store_urls():
            product_urls = await self._extract_product_urls_from_store(store_url)
            all_product_urls.extend(product_urls)

        if force_full_update:
            # Force full scraping for all products
            logger.info(
                f"Force full update enabled - performing full scraping for all {len(all_product_urls)} products"
            )
            return await self._scrape_new_products(all_product_urls)

        # Create diffjson stock updates for existing products
        in_stock_count, out_of_stock_count = await self.create_diffjson_stock_updates(
            all_product_urls, output_dir, force_full_update
        )

        # Find new products that need full scraping
        new_urls = []
        for url in all_product_urls:
            if not self._is_bean_already_scraped_anywhere(url):
                new_urls.append(url)

        logger.info(f"Found {in_stock_count} existing products for stock updates")
        logger.info(f"Found {out_of_stock_count} products now out of stock")
        logger.info(f"Found {len(new_urls)} new products for full scraping")

        # Perform full AI extraction only for new products
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

        # Create a function that returns the product URLs for the AI extraction
        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=False,  # Standard Shopify site, no JS needed
            translate_to_english=True,  # Translate Spanish to English for AI extraction
        )


    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from store page."""
        soup = await self.fetch_page(store_url, use_playwright=False)
        if not soup:
            return []

        # Use base class method with Shopify-specific patterns
        return self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/collections/"],
            selectors=[
                'a[href*="/collections/origenes/products/"]',  # Standard Shopify product links
                'a[href*="/collections/blends/products/"]',  # Standard Shopify product links
                '.product-item a',        # Common product item links
                '.grid-product__link',    # Shopify grid layout
                'h4 a',                   # Product title links (seen in their HTML)
            ]
        )