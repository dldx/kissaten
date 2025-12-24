"""Qima Coffee scraper implementation with AI-powered extraction."""

import logging
from pathlib import Path

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="qima-coffee",
    display_name="Qima Cafe",
    roaster_name="Qima Cafe",
    website="https://qimacafe.com",
    description="London-based specialty coffee roaster with life-changing coffee from Yemen, Ethiopia, and Colombia",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class QimaCoffeeScraper(BaseScraper):
    """Scraper for Qima Cafe with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Qima Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Qima Cafe",
            base_url="https://qimacafe.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the coffee collection URL
        """
        return ["https://qimacafe.com/collections/tree-to-cup?filter.v.availability=1"]


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
            use_playwright=False,  # Shopify works well with standard mode
        )

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from the store page.

        Args:
            store_url: URL of the coffee collection page

        Returns:
            List of product URLs for coffee products
        """
        soup = await self.fetch_page(store_url, use_playwright=False)
        if not soup:
            return []

        return [
            str(url).split("?")[0]
            for url in self.extract_product_urls_from_soup(
                soup,
                url_path_patterns=["/products/"],
                selectors=['a[href*="/products/"]'],
            )
        ]
