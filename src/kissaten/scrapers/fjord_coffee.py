"""Fjord Coffee scraper implementation with AI-powered extraction."""

import logging
from pathlib import Path

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="fjord-coffee",
    display_name="Fjord Coffee",
    roaster_name="Fjord Coffee Roasters",
    website="https://fjord-coffee.de",
    description="Berlin-based specialty coffee roaster focusing on quality and sustainability",
    requires_api_key=True,
    currency="EUR",
    country="Germany",
    status="available",
)
class FjordCoffeeScraper(BaseScraper):
    """Scraper for Fjord Coffee (fjord-coffee.de) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Fjord Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Fjord Coffee Roasters",
            base_url="https://fjord-coffee.de",
            rate_limit_delay=1.5,  # Be respectful with rate limiting
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
        return ["https://fjord-coffee.de/collections/coffee"]


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
            use_playwright=False,  # Shopify site, should work with simple HTTP
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

        # Custom selectors for Fjord Coffee (Shopify-based)
        custom_selectors = [
            'a[href*="/products/"]',
            ".product-item a",
            ".product-link a",
            "a.product-item-link",
            # Shopify common patterns
            'a[href*="/collections/coffee/products/"]',
            ".product-card a",
            ".product-grid-item a",
        ]

        product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/products/"],
            selectors=custom_selectors,
        )

        exclude_url_patterns = ["fjord-taster-set"]

        return [url for url in product_urls if not any(pattern in url for pattern in exclude_url_patterns)]