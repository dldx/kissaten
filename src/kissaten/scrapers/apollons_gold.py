"""Apollon's Gold scraper implementation with AI-powered extraction."""

import logging
from pathlib import Path

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="apollons-gold",
    display_name="Apollon's Gold",
    roaster_name="Apollon's Gold",
    website="https://shop.apollons-gold.com",
    description="Japanese specialty coffee roaster based in Tokyo, known for high-quality "
    "single origin coffees and exceptional geisha varieties",
    requires_api_key=True,
    currency="GBP",
    country="Japan",
    status="available",
)
class ApollonsGoldScraper(BaseScraper):
    """Scraper for Apollon's Gold (shop.apollons-gold.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Apollon's Gold scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Apollon's Gold",
            base_url="https://shop.apollons-gold.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the coffee collection URL
        """
        return ["https://shop.apollons-gold.com/collections/frontpage"]


    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction.

        Args:
            product_urls: List of URLs for new products

        Returns:
            List of newly scraped CoffeeBean objects
        """
        if not product_urls:
            return []

        # Create a function that returns the product URLs for the AI extraction
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
                # Shopify standard selectors
                'a[href*="/products/"]',
                '.product-item a',
                '.product-link',
                '.product-card a',
                '.product a',
                'h3 a',  # Product title links
                'h2 a',  # Alternative title links
                # Shopify collection page patterns
                '.product-card-wrapper a',
                '.card__content a',
                '.card-wrapper a',
                '.grid-product__content a',
                '.product-form__cart a',
            ],
        )

        # Filter out non-coffee products (subscriptions, gift cards, equipment, etc.)
        excluded_products = [
            "subscription",  # Subscription products
            "gift-card",  # Gift cards
            "gift",  # General gift items
            "wholesale",  # Wholesale products
            "equipment",  # Coffee equipment
            "brewing",  # Brewing equipment
            "accessory",  # Accessories
            "merchandise",  # Merchandise
        ]

        filtered_urls = []
        for url in product_urls:
            # Check if any excluded product identifier is in the URL
            if not any(excluded in url.lower() for excluded in excluded_products):
                filtered_urls.append(url)

        return filtered_urls
