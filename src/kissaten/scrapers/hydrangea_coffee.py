"""Hydrangea Coffee scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="hydrangea",
    display_name="Hydrangea Coffee",
    roaster_name="Hydrangea Coffee Roasters",
    website="https://hydrangea.coffee",
    description="Light, fruit-forward, experimental coffees",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="available",
)
class HydrangeaCoffeeScraper(BaseScraper):
    """Scraper for Hydrangea Coffee (hydrangea.coffee) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Hydrangea Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Hydrangea Coffee Roasters",
            base_url="https://hydrangea.coffee",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the main store URL
        """
        return ["https://hydrangea.coffee"]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Hydrangea Coffee using AI extraction.

        Returns:
            List of CoffeeBean objects
        """
        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=self._extract_product_urls_from_store,
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

        # Custom selectors for Hydrangea Coffee Shopify store
        custom_selectors = [
            'a[href*="/products/"]',
            ".product-item-link",
            ".product-link",
            "h3 > a",  # Product titles that are links
        ]

        product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/products/"],
            selectors=custom_selectors,
        )

        # Filter out non-coffee products
        filtered_urls = []
        for url in product_urls:
            if self._is_coffee_product_url(url):
                filtered_urls.append(url)

        return filtered_urls

    def _is_coffee_product_url(self, url: str) -> bool:
        """Filter out non-coffee products by URL.

        Args:
            url: Product URL to check

        Returns:
            True if this appears to be a coffee product URL
        """
        # Exclude equipment, subscriptions, and other non-coffee items
        excluded_patterns = [
            'kettle',
            'concentrate',
            'subscription',
            'rested-coffee',
            'garage-sale',
            'roasters-choice',
            'brewing',
            'equipment',
            'accessories'
        ]

        url_lower = url.lower()
        return not any(pattern in url_lower for pattern in excluded_patterns)
