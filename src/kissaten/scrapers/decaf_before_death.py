"""Decaf Before Death scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="decaf-before-death",
    display_name="Decaf Before Death",
    roaster_name="Decaf Before Death",
    website="https://www.decafbeforedeath.co.uk",
    description="UK-based specialty decaf coffee roaster offering experimental and traditional decaf processes",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class DecafBeforeDeathScraper(BaseScraper):
    """Scraper for Decaf Before Death (decafbeforedeath.co.uk) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Decaf Before Death scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Decaf Before Death",
            base_url="https://www.decafbeforedeath.co.uk",
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
        return ["https://www.decafbeforedeath.co.uk/collections/roastery"]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Decaf Before Death using AI extraction.

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

        # Custom selectors for Decaf Before Death's Shopify store
        custom_selectors = [
            'a[href*="/products/"]',
            '.product-item a',
            '.product-card a',
            '.grid-product__link',
        ]

        return self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/products/"],
            selectors=custom_selectors,
        )
