"""People's Possession Coffee scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="people-possession",
    display_name="People's Possession",
    roaster_name="People's Possession",
    website="https://peoplepossession.com",
    description="Radically sourced specialty coffee from Europe",
    requires_api_key=True,
    currency="EUR",
    country="Europe",
    status="available",
)
class PeoplePossessionScraper(BaseScraper):
    """Scraper for People's Possession Coffee (peoplepossession.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize People's Possession scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="People's Possession",
            base_url="https://peoplepossession.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the shop URL
        """
        return ["https://peoplepossession.com/shop/"]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from People's Possession shop using AI extraction.

        Returns:
            List of CoffeeBean objects
        """
        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=self._extract_product_urls_from_store,
            ai_extractor=self.ai_extractor,
            use_playwright=True,
            batch_size=1,  # Sequential processing for this scraper
        )

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from store page using Playwright.

        Args:
            store_url: URL of the store page

        Returns:
            List of product URLs
        """
        soup = await self.fetch_page(store_url, use_playwright=True)
        if not soup:
            return []

        return self.extract_product_urls_from_soup(
            soup, url_path_patterns=["/product/"], selectors=['a[href*="/product/"]']
        )
