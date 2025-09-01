"""Sweven Coffee scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="sweven",
    display_name="Sweven Coffee",
    roaster_name="Sweven Coffee",
    website="https://www.swevencoffee.co.uk",
    description="UK-based specialty coffee roaster focusing on rare, exclusive, and microlot coffees",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class SwevenCoffeeScraper(BaseScraper):
    """Scraper for Sweven Coffee (swevencoffee.co.uk) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Sweven Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Sweven Coffee",
            base_url="https://www.swevencoffee.co.uk",
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
        return ["https://www.swevencoffee.co.uk/coffee/"]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Sweven Coffee store using AI extraction.

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

        # Custom selectors for Sweven Coffee
        custom_selectors = [
            'a[href*="/product/"]',
            'a[href*="view product"]',
            '.product-item a',
            'h5 a',  # Product title links
            '.grid__item a',
        ]

        return self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/product/"],
            selectors=custom_selectors,
        )
