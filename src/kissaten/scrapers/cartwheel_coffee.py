"""Cartwheel Coffee scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="cartwheel",
    display_name="Cartwheel Coffee",
    roaster_name="Cartwheel Coffee",
    website="https://cartwheelcoffee.com",
    description="UK-based specialty coffee roaster",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class CartwheelCoffeeScraper(BaseScraper):
    """Scraper for Cartwheel Coffee (cartwheelcoffee.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Cartwheel Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Cartwheel Coffee",
            base_url="https://cartwheelcoffee.com",
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
        return ["https://cartwheelcoffee.com/pages/store"]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Cartwheel Coffee store using AI extraction.

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

        # Custom selectors for Cartwheel Coffee
        custom_selectors = [
            "a.shop-img_hover.is--store.w-inline-block",
            'a[class*="shop-img_hover"]',
            'a[href*="/products/"]',
        ]

        return self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/products/"],
            selectors=custom_selectors,
        )
