"""Apollon's Gold scraper implementation with AI-powered extraction."""

import logging
from pathlib import Path

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="apollons-gold",
    display_name="Apollon's Gold",
    roaster_name="Apollon's Gold",
    website="https://shop.apollons-gold.com",
    description="Japanese specialty coffee roaster based in Tokyo, known for high-quality "
    "single origin coffees and exceptional geisha varieties",
    requires_api_key=True,
    currency="GBP",
    country="Japan",
    status="available",
)
class ApollonsGoldScraper(BaseScraper):
    """Scraper for Apollon's Gold (shop.apollons-gold.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Apollon's Gold scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Apollon's Gold",
            base_url="https://shop.apollons-gold.com",
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
        return ["https://shop.apollons-gold.com/collections/frontpage"]

    async def scrape(self, force_full_update: bool = False) -> list[CoffeeBean]:
        """Scrape coffee beans from Apollon's Gold with efficient stock updates.

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
            return await self._scrape_new_products(list(set(new_urls)))

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
                # Shopify standard selectors
                'a[href*="/products/"]',
                '.product-item a',
                '.product-link',
                '.product-card a',
                '.product a',
                'h3 a',  # Product title links
                'h2 a',  # Alternative title links
                # Shopify collection page patterns
                '.product-card-wrapper a',
                '.card__content a',
                '.card-wrapper a',
                '.grid-product__content a',
                '.product-form__cart a',
            ],
        )

        # Filter out non-coffee products (subscriptions, gift cards, equipment, etc.)
        excluded_products = [
            "subscription",  # Subscription products
            "gift-card",  # Gift cards
            "gift",  # General gift items
            "wholesale",  # Wholesale products
            "equipment",  # Coffee equipment
            "brewing",  # Brewing equipment
            "accessory",  # Accessories
            "merchandise",  # Merchandise
        ]

        filtered_urls = []
        for url in product_urls:
            # Check if any excluded product identifier is in the URL
            if not any(excluded in url.lower() for excluded in excluded_products):
                filtered_urls.append(url)

        return filtered_urls
