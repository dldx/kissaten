"""Alchemy Coffee scraper implementation with AI-powered extraction."""

import logging

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

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the store URLs for filter and espresso coffee
        """
        return [
            "https://alchemycoffee.co.uk/product-category/coffee/filter-coffee-selection-alchemy-coffee/",
            "https://alchemycoffee.co.uk/product-category/coffee/espresso/",
        ]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Alchemy Coffee using AI extraction.

        Returns:
            List of CoffeeBean objects
        """
        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=self._extract_product_urls_from_store,
            ai_extractor=self.ai_extractor,
            use_playwright=False,
            batch_size=2,
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

        return self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/product/"],
            selectors=custom_selectors,
        )
