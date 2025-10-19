"""Ona Coffee scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="ona-coffee",
    display_name="Ona Coffee",
    roaster_name="Ona Coffee",
    website="https://onacoffee.com.au",
    description="Award-winning Australian specialty coffee roaster based in Canberra, "
    "focusing on single-origin beans and distinctive blends",
    requires_api_key=True,
    currency="AUD",
    country="Australia",
    status="available",
)
class OnaCoffeeScraper(BaseScraper):
    """Scraper for Ona Coffee (onacoffee.com.au) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Ona Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Ona Coffee",
            base_url="https://onacoffee.com.au",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the main coffee collections
        """
        return [
            "https://onacoffee.com.au/collections/filter",
            "https://onacoffee.com.au/collections/espresso",
            "https://onacoffee.com.au/collections/milk-based",
            "https://onacoffee.com.au/collections/reserve",
            "https://onacoffee.com.au/collections/rare-coffee",
            "https://onacoffee.com.au/collections/special-release",
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
            use_optimized_mode=False,
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
                # Standard Shopify product link selectors
                'a[href*="/products/"]',
                '.product-item a',
                '.product-link',
                '.product-card a',
                '.product a',
                '.grid-product__link',
                '.card-wrapper a',
                'h3 a',  # Product title links
                'h4 a',  # Alternative title links
                '.product-form a',
                '.product-info a',
            ],
        )

        # Filter out non-coffee products (subscriptions, gift cards, brew gear, etc.)
        excluded_products = [
            "subscription",  # Coffee subscriptions
            "gift-card",  # Gift cards
            "gift",  # General gift items
            "brew-gear",  # Brewing equipment
            "equipment",  # Equipment
            "drip-bag",  # Drip bags
            "candy",  # Candy/sweets
            "merchandise",  # Merchandise
            "brewing",  # Brewing accessories
            "wholesale",  # Wholesale products
            "bundle",  # Bundles
            "the-dog-house-coffee-collection",
            "paragon",
        ]

        filtered_urls = []
        for url in product_urls:
            if url and isinstance(url, str) and not any(excluded in url.lower() for excluded in excluded_products):
                filtered_urls.append(url)

        logger.info(f"Found {len(filtered_urls)} coffee product URLs from {store_url}")
        return filtered_urls
