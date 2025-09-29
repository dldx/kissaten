"""Leaves Coffee scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="leaves-coffee",
    display_name="Leaves Coffee",
    roaster_name="Leaves Coffee Roasters",
    website="https://leavescoffee.jp",
    description="Japanese specialty coffee roaster based in Tokyo, focusing on single-origin "
    "coffees and carefully crafted blends with detailed flavor profiling",
    requires_api_key=True,
    currency="JPY",
    country="Japan",
    status="available",
)
class LeavesCoffeeScraper(BaseScraper):
    """Scraper for Leaves Coffee (leavescoffee.jp) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Leaves Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Leaves Coffee Roasters",
            base_url="https://leavescoffee.jp",
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
            "https://leavescoffee.jp/en/shop",
            "https://leavescoffee.jp/en/shop/coffee",
        ]


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
                # Leaves Coffee specific selectors
                'a[href*="/en/products/"]',
                'h3 a',  # Product title links
                'h4 a',  # Alternative title links
            ],
        )

        # Filter out non-coffee products (subscriptions, trios, merchandise, etc.)
        excluded_products = [
            "subscription",  # Subscription products
            "trio",  # Trio products like "THE AFRICAN TRIO"
            "gift-card",  # Gift cards
            "gift",  # General gift items
            "merchandise",  # Merchandise like t-shirts, tote bags
            "equipment",  # Coffee equipment
            "accessory",  # Accessories
            "t-shirt",  # T-shirts
            "tote-bag",  # Tote bags
            "spoon",  # Cupping spoons
            "paper-wave",  # Paper filters
            "lab",  # Lab equipment
            "water",  # Brewing water
            "drip-bag",  # Drip bag sets
            "collection",  # Product collections/sets
            "home-pack",  # Home brewing packs
        ]

        filtered_urls = []
        for url in product_urls:
            # Check if any excluded product identifier is in the URL
            url_lower = url.lower()
            if not any(excluded in url_lower for excluded in excluded_products):
                # Additional check for trio products by name
                if "trio" not in url_lower and "african-trio" not in url_lower:
                    filtered_urls.append(url)

        return filtered_urls
