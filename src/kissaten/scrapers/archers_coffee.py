"""Archers Coffee scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="archers-coffee",
    display_name="Archers Coffee",
    roaster_name="Archers Coffee",
    website="https://archerscoffee.com",
    description="Dubai-based specialty coffee roaster offering meticulously sourced and roasted "
    "single-origin coffees, pour-over selections, espresso blends, and bespoke blends",
    requires_api_key=True,
    currency="AED",
    country="United Arab Emirates",
    status="available",
)
class ArchersCoffeeScraper(BaseScraper):
    """Scraper for Archers Coffee (archerscoffee.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Archers Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Archers Coffee",
            base_url="https://archerscoffee.com",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the coffee collection URLs
        """
        return [
            "https://archerscoffee.com/collections/espresso-milk-coffees-2025?page=1",
            "https://archerscoffee.com/collections/espresso-milk-coffees-2025?page=2",
            "https://archerscoffee.com/collections/pour-over-coffees-2025?page=1",
            "https://archerscoffee.com/collections/pour-over-coffees-2025?page=2",
            "https://archerscoffee.com/collections/pour-over-coffees-2025?page=3",
            "https://archerscoffee.com/collections/bespoke-blends-2025",
        ]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Archers Coffee using AI extraction.

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
        product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/products/"],
            selectors=[
                # Generic product link selectors
                'a[href*="/products/"]',
                '.product-item a',
                '.product-link',
                '.product-card a',
                '.product a',
                # Archers specific selectors
                'a[href*="/collections/espresso-milk-coffees-2025/products/"]',
                'a[href*="/collections/pour-over-coffees-2025/products/"]',
                'a[href*="/collections/bespoke-blends-2025/products/"]',
                'h3 a',  # Product title links
                'h4 a',  # Alternative title links
            ],
        )

        # Filter out non-coffee products (subscriptions, equipment, etc.)
        excluded_products = [
            "subscription",  # Subscription products
            "gift-card",  # Gift cards
            "gift",  # General gift items
            "wholesale",  # Wholesale products
            "equipment",  # Coffee equipment
            "accessory",  # Accessories
            "merchandise",  # Merchandise
            "academy",  # Coffee academy products
            "bundle",  # Product bundles
        ]

        filtered_urls = []
        for url in product_urls:
            # Check if any excluded product identifier is in the URL
            if not any(excluded in url.lower() for excluded in excluded_products):
                filtered_urls.append(url)

        return filtered_urls
