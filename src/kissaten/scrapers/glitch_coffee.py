"""Glitch Coffee scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="glitch",
    display_name="Glitch Coffee",
    roaster_name="Glitch Coffee & Roasters",
    website="https://shop.glitchcoffee.com",
    description="Specialty coffee roasters from Japan with unique processing methods",
    requires_api_key=True,
    currency="JPY",
    country="Japan",
    status="available",
)
class GlitchCoffeeScraper(BaseScraper):
    """Scraper for Glitch Coffee (shop.glitchcoffee.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Glitch Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Glitch Coffee & Roasters",
            base_url="https://shop.glitchcoffee.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the main collection URLs with pagination
        """
        return [
            "https://shop.glitchcoffee.com/en/collections/all",
            "https://shop.glitchcoffee.com/en/collections/all?page=2",
            # Add more pages as needed - they show 32 products per page
        ]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Glitch Coffee using AI extraction.

        Returns:
            List of CoffeeBean objects
        """
        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=self._extract_product_urls_from_store,
            ai_extractor=self.ai_extractor,
            use_playwright=False,  # Static Shopify site should work with regular requests
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

        # Custom selectors for Glitch Coffee Shopify store
        custom_selectors = [
            'a[href*="/en/products/"]',
            ".product-item-link",
            ".product-link",
            "h3 > a",  # Product titles that are links
            ".grid-product__title a",  # Common Shopify pattern
        ]

        product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/en/products/"],
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
        # Exclude equipment, merchandise, and other non-coffee items
        excluded_patterns = [
            't-shirt',
            'tshirt',
            'shirt',
            'merchandise',
            'merch',
            'collaboration',
            'equipment',
            'accessories',
            'brewing',
            'kettle',
            'grinder',
            'subscription',
        ]

        url_lower = url.lower()
        return not any(pattern in url_lower for pattern in excluded_patterns)
