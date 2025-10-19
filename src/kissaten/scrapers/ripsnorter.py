"""Ripsnorter Coffee scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="ripsnorter",
    display_name="Ripsnorter Coffee",
    roaster_name="Ripsnorter",
    website="https://ripsnorter.nl",
    description="Dutch specialty coffee roaster focusing on high-quality single origins",
    requires_api_key=True,
    currency="EUR",
    country="Netherlands",
    status="available",
)
class RipsnorterScraper(BaseScraper):
    """Scraper for Ripsnorter Coffee (ripsnorter.nl) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Ripsnorter scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Ripsnorter",
            base_url="https://ripsnorter.nl",
            rate_limit_delay=1.5,  # Be respectful with rate limiting
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
        return ["https://ripsnorter.nl/collections/frontpage?country=NL"]


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

        # Extract all product URLs using base class method
        product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/products/"],
            selectors=[
                'a[href*="/products/"]',
                ".product-item a",
                ".product-link",
            ],
        )

        # Filter out non-coffee products (drip bags and subscriptions as requested)
        filtered_urls = []
        for url in product_urls:
            if url and isinstance(url, str) and self._is_coffee_product_url(url):
                filtered_urls.append(url)

        return filtered_urls

    def _is_coffee_product_url(self, url: str) -> bool:
        """Filter out non-coffee products."""
        # Exclude drip bags and subscriptions as requested
        excluded_patterns = [
            "drip-bag",
            "subscription",
            "gift-card",
            "experience",  # Covers subscription experiences
        ]

        url_lower = url.lower()
        for pattern in excluded_patterns:
            if pattern in url_lower:
                return False

        return True

    def _is_coffee_product(self, name: str) -> bool:
        """Check if this product is actually coffee beans (not drip bags/subscriptions)."""
        # Use base class method but add custom exclusions
        if not self.is_coffee_product_name(name):
            return False

        # Additional exclusions specific to Ripsnorter
        excluded_terms = [
            "drip bag",
            "subscription",
            "experience",
            "gift card",
        ]

        name_lower = name.lower()
        for term in excluded_terms:
            if term in name_lower:
                return False

        return True
