"""Klover Club scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="klover-club",
    display_name="Klover Club",
    roaster_name="Klover Club",
    website="https://klovercoffee.com",
    description="Specialty coffee roaster based in Paris, France",
    requires_api_key=True,
    currency="GBP",  # British Pound
    country="France",
    status="available",
)
class KloverClubScraper(BaseScraper):
    """Scraper for Klover Club (klovercoffee.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Klover Club scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Klover Club",
            base_url="https://klovercoffee.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the store URL
        """
        return ["https://klovercoffee.com/collections/all"]

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction.

        Args:
            product_urls: List of URLs for new products

        Returns:
            List of newly scraped CoffeeBean objects
        """

        # Create a function that returns the product URLs for the AI extraction
        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=False,
            use_optimized_mode=False,
        )

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from store page.

        Args:
            store_url: URL of the store page

        Returns:
            List of product URLs
        """
        soup = await self.fetch_page(store_url, use_playwright=False)
        if not soup:
            return []

        # Extract all product URLs and filter out sold out items
        all_product_urls = []
        all_product_url_el = soup.select('a[href*="/products/"]')
        for el in all_product_url_el:
            # Check if "Sold out" appears in the parent elements
            if "Sold out" not in el.parent.parent.text:
                href = el.get('href')
                if href:
                    all_product_urls.append(self.base_url + href.replace('\n', '').strip().split('?')[0])

        # Filter out excluded products (merchandise and non-coffee items)
        excluded_products = [
            "merchandise",
            "equipment",
            "subscription",
            "sample-box",
            "gift",
            "giftcard",
        ]

        filtered_urls = []
        for url in all_product_urls:
            if url and isinstance(url, str) and not any(excluded in url.lower() for excluded in excluded_products):
                filtered_urls.append(url)

        logger.info(f"Found {len(filtered_urls)} available coffee product URLs")
        return list(set(filtered_urls))
