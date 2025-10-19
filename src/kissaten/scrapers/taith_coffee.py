"""Scraper for Taith Coffee.

Taith Coffee is a specialty coffee roaster based in Lewes, UK.
Website: https://taithcoffee.com
"""

import logging
from pathlib import Path

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="taith-coffee",
    display_name="Taith Coffee",
    roaster_name="Taith Coffee",
    website="https://taithcoffee.com",
    description="Specialty coffee roaster from Lewes, UK",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class TaithCoffeeScraper(BaseScraper):
    """Scraper for Taith Coffee with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Taith Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Taith Coffee",
            base_url="https://taithcoffee.com",
            rate_limit_delay=1.0,
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
        return ["https://taithcoffee.com/shop/coffee"]

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

        if self.ai_extractor:
            return await self.scrape_with_ai_extraction(
                extract_product_urls_function=get_new_product_urls,
                ai_extractor=self.ai_extractor,
                use_playwright=False,
            )
        logger.warning("AI extractor not available - traditional scraping not implemented for atmans Coffee")
        return []


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

        # Custom selectors for Taith Coffee's Squarespace structure
        custom_selectors = [
            'a[href*="/shop/p/"]',  # Direct product links
            ".product-link",  # Generic product links
            ".product-item a",  # Product item links
        ]

        # Use the base class method for extracting product URLs
        return self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/shop/p/"],
            selectors=custom_selectors,
        )
