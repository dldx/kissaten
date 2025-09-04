"""Friedhats coffee roaster scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="friedhats",
    display_name="Friedhats",
    roaster_name="Friedhats",
    website="https://friedhats.com",
    description="Specialty coffee roaster from Rotterdam",
    requires_api_key=True,
    currency="EUR",
    country="Netherlands",  # Assuming based on EUR currency
    status="available",
)
class FriedhatsScraper(BaseScraper):
    """Scraper for Friedhats (friedhats.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Friedhats scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Friedhats",
            base_url="https://friedhats.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the store URL
        """
        return ["https://friedhats.com/collections/coffees"]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Friedhats using AI extraction.

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
        soup = await self.fetch_page(store_url, use_playwright=True)
        if not soup:
            return []

        # Use the base class method with Shopify-specific patterns
        # Friedhats appears to be a Shopify store based on the /products/ URLs
        return self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/products/"],
            selectors=[
                # Common Shopify selectors
                'a[href*="/products/"]',
                ".product-item a",
                ".product-link",
                ".grid-product__link",
                ".card__link",
                # Add more specific selectors if needed
            ],
        )
