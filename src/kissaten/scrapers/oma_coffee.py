"""Oma Coffee Roaster scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="oma",
    display_name="Oma Coffee Roaster",
    roaster_name="Oma Coffee Roaster",
    website="https://omacoffeeroaster.com",
    description="Hong Kong-based specialty coffee roaster focusing on filter coffee and single origins",
    requires_api_key=True,
    currency="HKD",
    country="Hong Kong",
    status="available",
)
class OmaCoffeeScraper(BaseScraper):
    """Scraper for Oma Coffee Roaster (omacoffeeroaster.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Oma Coffee Roaster scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Oma Coffee Roaster",
            base_url="https://omacoffeeroaster.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the store URLs
        """
        return [
            "https://omacoffeeroaster.com/collections/coffee",
        ]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Oma Coffee Roaster store using AI extraction.

        Returns:
            List of CoffeeBean objects
        """
        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=self._extract_product_urls_from_store,
            ai_extractor=self.ai_extractor,
            use_playwright=True,
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

        # Custom selectors for Oma Coffee Roaster (Shopify-based)
        custom_selectors = [
            'a[href*="/products/"]',
            ".product-item a",
            ".grid__item a",
            "a.product-link",
            "h3 a",  # Product title links
        ]

        return self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/products/"],
            selectors=custom_selectors,
        )
