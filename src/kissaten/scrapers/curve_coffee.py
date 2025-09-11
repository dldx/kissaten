"""Curve Coffee Roasters scraper.

UK-based specialty coffee roaster offering single origin coffees with detailed
origin stories and producer information.
"""

import logging
from pathlib import Path

from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="curve-coffee",
    display_name="Curve Coffee Roasters",
    roaster_name="Curve Coffee Roasters",
    website="https://www.curveroasters.co.uk",
    description="UK specialty coffee roaster offering single origin coffees "
    "with detailed origin stories and producer information",
    requires_api_key=True,  # Using AI extraction for complex Squarespace site
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class CurveCoffeeScraper(BaseScraper):
    """Scraper for Curve Coffee Roasters."""

    def __init__(self, api_key: str | None = None):
        """Initialize the scraper.

        Args:
            api_key: Optional API key for AI-powered extraction
        """
        super().__init__(
            roaster_name="Curve Coffee Roasters",
            base_url="https://www.curveroasters.co.uk",
            rate_limit_delay=1.5,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor (recommended for complex Squarespace sites)
        self.ai_extractor = None
        try:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
        except ImportError:
            logger.warning("AI extractor not available - falling back to traditional extraction")

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the store URLs to scrape
        """
        return [
            "https://www.curveroasters.co.uk/shop-coffee?category=Coffee",
            # Could also include other coffee categories if needed:
            # "https://www.curveroasters.co.uk/shop-coffee?category=Espresso",
            # "https://www.curveroasters.co.uk/shop-coffee?category=Filter",
            # "https://www.curveroasters.co.uk/shop-coffee?category=Decaf",
        ]

    async def scrape(self, force_full_update: bool = False) -> list[CoffeeBean]:
        """Scrape coffee beans from Curve Coffee.

        Args:
            force_full_update: If True, force full extraction of all products instead of
                             creating diffjson updates for existing products

        Returns:
            List of CoffeeBean objects
        """
        # Use the AI-powered scraping workflow (recommended for Squarespace sites)
        if not self.ai_extractor:
            logger.error("AI extractor not available - Curve Coffee requires AI extraction")
            return []

        # Start session for tracking scraped products
        self.start_session()

        # If forcing full update, use the AI extraction directly
        if force_full_update:
            return await self.scrape_with_ai_extraction(
                extract_product_urls_function=self._extract_product_urls_from_store,
                ai_extractor=self.ai_extractor,
                use_playwright=True,  # Squarespace sites often need JS rendering
            )

        # Otherwise use the efficient update workflow
        return await self._scrape_new_products()

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

        # Use the base class method with Squarespace-specific patterns
        urls = self.extract_product_urls_from_soup(
            soup,
            # Curve Coffee product URL pattern
            url_path_patterns=["/shop-coffee/"],
            selectors=[
                # Squarespace product link selectors
                'a[href*="/shop-coffee/"]',
                ".sqs-block-image a",
                ".summary-title a",
                ".summary-item a",
                "a.summary-excerpt-only",
                # Coffee-specific exclusions will be handled by the filtering
            ],
        )

        return self.deduplicate_urls(urls)

    async def _scrape_new_products(self) -> list[CoffeeBean]:
        """Scrape only new products, update existing ones with diffjson.

        Returns:
            List of newly scraped CoffeeBean objects
        """
        output_dir = Path("data")
        all_product_urls = []

        # Get all product URLs from store pages
        for store_url in self.get_store_urls():
            product_urls = await self._extract_product_urls_from_store(store_url)
            all_product_urls.extend(product_urls)

        all_product_urls = self.deduplicate_urls(all_product_urls)
        logger.info(f"Found {len(all_product_urls)} coffee product URLs out of {len(all_product_urls)} total products")

        # Create diffjson stock updates for existing products
        in_stock_count, out_of_stock_count = await self.create_diffjson_stock_updates(all_product_urls, output_dir)

        # Find new products that need full scraping
        new_urls = []
        for url in all_product_urls:
            if not self._is_bean_already_scraped_anywhere(url):
                new_urls.append(url)

        if in_stock_count > 0:
            logger.info(f"Found {in_stock_count} existing products for stock updates")
        if out_of_stock_count > 0:
            logger.info(f"Found {out_of_stock_count} products now out of stock")
        logger.info(f"Found {len(new_urls)} new products for full scraping")

        # Scrape new products with full AI extraction
        if new_urls:
            return await self._scrape_only_new_products(new_urls)

        return []

    async def _scrape_only_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
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
        )
