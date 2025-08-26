"""Standout Coffee scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="standout",
    display_name="Standout Coffee",
    roaster_name="Standout Coffee AB",
    website="standoutcoffee.com",
    description="Swedish specialty coffee roaster from Stockholm",
    requires_api_key=True,
    currency="GBP",  # Website shows GBP pricing
    country="Sweden",
    status="available",
)
class StandoutCoffeeScraper(BaseScraper):
    """Scraper for Standout Coffee (standoutcoffee.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Standout Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Standout Coffee AB",
            base_url="https://www.standoutcoffee.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the store URLs for different coffee collections
        """
        return [
            "https://www.standoutcoffee.com/collections/featured-collection",
            "https://www.standoutcoffee.com/collections/specialty-coffee",
            "https://www.standoutcoffee.com/collections/competition-coffee",
            "https://www.standoutcoffee.com/collections/historic-coffee",
        ]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Standout Coffee using AI extraction.

        Returns:
            List of CoffeeBean objects
        """
        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=self._extract_product_urls_from_store,
            ai_extractor=self.ai_extractor,
            use_playwright=False,  # Start with basic scraping, can enable if needed
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

        # Shopify-based store, use standard selectors plus custom ones
        custom_selectors = [
            'a[href*="/products/"]',
            ".product-item a",
            ".product-card a",
            ".grid-product__link",
            'a[class*="product"]',
        ]

        product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/products/"],
            selectors=custom_selectors,
        )

        # Filter out equipment and non-coffee products
        filtered_urls = []
        for url in product_urls:
            if self._is_coffee_product_url(url):
                filtered_urls.append(url)

        return filtered_urls

    def _is_coffee_product_url(self, url: str) -> bool:
        """Filter out non-coffee products by URL patterns.

        Args:
            url: Product URL to check

        Returns:
            True if URL appears to be for coffee beans
        """
        # Exclude equipment and accessories
        excluded_patterns = [
            "meter", "tds", "digital", "water", "brewer", "orea",
            "grinder", "equipment", "accessories", "subscription",
            "gift", "merch", "capsule", "capsules"
        ]

        url_lower = url.lower()
        return not any(pattern in url_lower for pattern in excluded_patterns)
