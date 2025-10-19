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
    description="Specialty coffee roaster offering modern and traditional expressions with direct trade relationships",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
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

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the all-coffee collection URL
        """
        return ["https://www.modcup.com/collections/all-coffee"]


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

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
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
        product_urls = list(
            set(
                [
                    f"https://www.modcup.com{href}"
                    for a in soup.select('a[href*="/all-coffee/"]')
                    if (href := a.get("href")) and isinstance(href, str)
                ]
            )
        )

        # Filter out non-coffee products (gift cards, etc.)
        excluded_products = [
            "gift-card",  # Gift cards
            "gift",  # General gift items
            "subscription",  # Subscription products if any
            "merchandise",  # Non-coffee merchandise
        ]

        filtered_urls = []
        for url in product_urls:
            if url and isinstance(url, str) and not any(excluded in url.lower() for excluded in excluded_products):
                filtered_urls.append(url)

        return filtered_urls
