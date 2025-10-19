"""Alchemy Coffee scraper implementation with AI-powered extraction."""

import logging
from pathlib import Path

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="alchemy-coffee",
    display_name="Alchemy Coffee",
    roaster_name="Alchemy Coffee",
    website="https://alchemycoffee.co.uk",
    description="London-based specialty coffee roaster with filter and espresso selections",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class AlchemyCoffeeScraper(BaseScraper):
    """Scraper for Alchemy Coffee (alchemycoffee.co.uk) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Alchemy Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Alchemy Coffee",
            base_url="https://alchemycoffee.co.uk",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the store URLs for filter and espresso coffee
        """
        return [
            "https://alchemycoffee.co.uk/product-category/coffee/filter-coffee-selection-alchemy-coffee/",
            "https://alchemycoffee.co.uk/product-category/coffee/espresso/",
        ]


    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction.

        Args:
            product_urls: List of URLs for new products

        Returns:
            List of newly scraped CoffeeBean objects
        """

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

        # Custom selectors for Alchemy Coffee's WooCommerce structure
        custom_selectors = [
            'a[href*="/product/"]',  # Direct product links
            ".woocommerce-LoopProduct-link",  # WooCommerce product links
            ".product-link",  # Generic product links
            "h3 a",  # Product title links
            ".wc-block-grid__product a",  # Block-based product grid links
        ]

        # Extract all product URLs using the base class method
        all_product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/product/"],
            selectors=custom_selectors,
        )

        # Filter coffee products
        coffee_urls = []
        for url in all_product_urls:
            if self.is_coffee_product_url(url, required_path_patterns=["/product/"]):
                coffee_urls.append(url)

        logger.info(f"Found {len(coffee_urls)} coffee product URLs out of {len(all_product_urls)} total products")
        return coffee_urls
