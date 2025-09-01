"""Nostos Coffee scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="nostos",
    display_name="Nostos Coffee",
    roaster_name="Nostos Coffee",
    website="https://nostoscoffee.co.uk",
    description="London-based specialty coffee roaster with locations in Battersea",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class NostosCoffeeScraper(BaseScraper):
    """Scraper for Nostos Coffee (nostoscoffee.co.uk) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Nostos Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Nostos Coffee",
            base_url="https://nostoscoffee.co.uk",
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
        return ["https://nostoscoffee.co.uk/collections/all-products"]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Nostos Coffee using AI extraction.

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

        # Shopify-specific selectors for Nostos Coffee
        custom_selectors = [
            'a[href*="/products/"]',
            ".product-item a",
            ".product-link",
            "h3 a",  # Often used for product titles with links
            ".card-wrapper a",  # Common Shopify card wrapper
        ]

        product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/products/"],
            selectors=custom_selectors,
        )

        # Filter out non-coffee products specific to Nostos Coffee
        filtered_urls = []
        for url in product_urls:
            if self._is_coffee_product_url(url):
                filtered_urls.append(url)

        return filtered_urls

    def _is_coffee_product_url(self, url: str) -> bool:
        """Filter out non-coffee products based on URL patterns."""
        # Exclude equipment, accessories, and non-coffee items
        excluded_patterns = [
            "origami",
            "cup",
            "dripper",
            "filter",
            "grinder",
            "equipment",
            "merch",
            "accessories",
            "gift",
            "subscription",
        ]

        url_lower = url.lower()
        for pattern in excluded_patterns:
            if pattern in url_lower:
                return False

        return True
