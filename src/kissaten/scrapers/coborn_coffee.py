"""Coborn Coffee scraper implementation with AI-powered extraction."""

import logging
from pathlib import Path

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="coborn",
    display_name="Coborn Coffee",
    roaster_name="Coborn Coffee",
    website="https://coborncoffee.com",
    description="UK-based specialty coffee roaster",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class CobornCoffeeScraper(BaseScraper):
    """Scraper for Coborn Coffee (coborncoffee.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Coborn Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Coborn Coffee",
            base_url="https://www.coborncoffee.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the shop URL
        """
        return ["https://www.coborncoffee.com/shop/coffee"]


    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction.

        Args:
            product_urls: List of URLs for new products

        Returns:
            List of newly scraped CoffeeBean objects
        """

        # Create a function that returns the product URLs for the AI extraction
        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=True,  # Use Playwright for JavaScript-rendered content
        )

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from store page.

        Args:
            store_url: URL of the store page

        Returns:
            List of product URLs
        """
        # Use Playwright for JavaScript-rendered content (Squarespace)
        soup = await self.fetch_page(store_url, use_playwright=True)
        if not soup:
            return []

        # Custom selectors for Coborn Coffee (Squarespace site)
        custom_selectors = [
            'a[href*="/shop/p/"]',  # Direct product links
            ".ProductList-item a",  # Product list items
            ".grid-item a",  # Grid layout items
            ".sqs-block-product a",  # Product blocks
            ".product-block a",  # Product blocks
            'a[href*="/products/"]',  # Alternative product links
        ]

        # Extract all product URLs using the base class method
        all_product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/shop/p/", "/products/"],
            selectors=custom_selectors,
        )

        excluded_paths = ["fortnightly-pzryf"]

        # Filter coffee products
        coffee_urls = []
        for url in all_product_urls:
            if self.is_coffee_product_url(url, required_path_patterns=["/shop/p/", "/products/"]) and not any(
                ep in url for ep in excluded_paths
            ):
                coffee_urls.append(url)

        logger.info(f"Found {len(coffee_urls)} coffee product URLs out of {len(all_product_urls)} total products")
        return coffee_urls
