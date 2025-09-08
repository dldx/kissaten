"""Modcup Coffee scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="modcup-coffee",
    display_name="Modcup Coffee",
    roaster_name="Modcup Coffee",
    website="https://www.modcup.com",
    description="Specialty coffee roaster offering modern and traditional expressions "
    "with direct trade relationships",
    requires_api_key=True,
    currency="GBP",
    country="UK",
    status="available",
)
class ModcupCoffeeScraper(BaseScraper):
    """Scraper for Modcup Coffee (modcup.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Modcup Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Modcup Coffee",
            base_url="https://www.modcup.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the all-coffee collection URL
        """
        return ["https://www.modcup.com/collections/all-coffee"]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Modcup Coffee using AI extraction.

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
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        # Get all product URLs using the base class method
        product_urls = list(set(["https://www.modcup.com" + a.get("href") for a in soup.select('a[href*="/all-coffee/"]') if a.get("href")]))

        # Filter out non-coffee products (gift cards, etc.)
        excluded_products = [
            "gift-card",  # Gift cards
            "gift",  # General gift items
            "subscription",  # Subscription products if any
            "merchandise",  # Non-coffee merchandise
        ]

        filtered_urls = []
        for url in product_urls:
            # Check if any excluded product identifier is in the URL
            if not any(excluded in url.lower() for excluded in excluded_products):
                filtered_urls.append(url)

        return filtered_urls
