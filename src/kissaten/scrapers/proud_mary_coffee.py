"""Proud Mary Coffee scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="proud-mary",
    display_name="Proud Mary Coffee",
    roaster_name="Proud Mary Coffee USA",
    website="https://proudmarycoffee.com",
    description="Specialty coffee roaster from Portland and Austin",
    requires_api_key=True,
    currency="GBP",
    country="United States",
    status="available",
)
class ProudMaryCoffeeScraper(BaseScraper):
    """Scraper for Proud Mary Coffee (proudmarycoffee.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Proud Mary Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Proud Mary Coffee USA",
            base_url="https://proudmarycoffee.com",
            rate_limit_delay=1.5,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the main coffee collection URL
        """
        return ["https://proudmarycoffee.com/collections/all-coffee"]


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
            use_playwright=True,
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

        # Custom selectors for Proud Mary Coffee Shopify store
        custom_selectors = [
            'a[href*="/products/"]',
            ".product-item-link",
            ".product-link",
            "h3 > a",  # Product titles that are links
            ".product-title a",
        ]

        product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/products/"],
            selectors=custom_selectors,
        )

        # Filter out non-coffee products
        filtered_urls = []
        for url in product_urls:
            if url and isinstance(url, str) and self._is_coffee_product_url(url):
                filtered_urls.append(url)

        return filtered_urls

    def _is_coffee_product_url(self, url: str) -> bool:
        """Filter out non-coffee products by URL.

        Args:
            url: Product URL to check

        Returns:
            True if this appears to be a coffee product URL
        """
        # Exclude subscriptions, bundles, and other non-individual coffee items
        excluded_patterns = [
            'subscription',
            'deluxe-subscription',
            'wild-coffee-subscription',
            'curious-coffee-subscription',
            'mild-coffee-subscription',
            'surpriseme',
            'picnmix',
            'pic-n-mix',
            'coffee-subscriptions',
            'instant-coffee',  # Exclude instant coffee
            'bundle',
            'gift',
        ]

        url_lower = url.lower()
        return not any(pattern in url_lower for pattern in excluded_patterns)
