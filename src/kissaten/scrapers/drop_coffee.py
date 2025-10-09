"""Drop Coffee scraper implementation with AI-powered extraction."""

import logging
from pathlib import Path

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="drop-coffee",
    display_name="Drop Coffee",
    roaster_name="Drop Coffee Roasters",
    website="https://dropcoffee.com",
    description="Swedish specialty coffee roaster focusing on sweetness, clarity and vibrancy",
    requires_api_key=True,
    currency="SEK",
    country="Sweden",
    status="available",
)
class DropCoffeeScraper(BaseScraper):
    """Scraper for Drop Coffee (dropcoffee.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Drop Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Drop Coffee Roasters",
            base_url="https://www.dropcoffee.com",
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
        return ["https://www.dropcoffee.com/collections/beans"]


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

        # Custom selectors for Drop Coffee (Shopify-based)
        custom_selectors = [
            'a[href*="/products/"]',
            ".product-item a",
            ".product-link a",
            "a.product-item-link",
            # Shopify common patterns
            'a[href*="/collections/beans/products/"]',
            ".product-title a",
            ".product-card a",
            ".grid-product__link",
        ]

        # Extract all product URLs using the base class method
        all_product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/products/"],
            selectors=custom_selectors,
        )

        excluded_urls = ["drop-coffee-tasting-pack", "little-drop-single-brew-kit", "advent-kalender"]

        # Filter coffee products using base class method
        coffee_urls = []
        for url in all_product_urls:
            if self.is_coffee_product_url(url, required_path_patterns=["/products/"]) and not any(
                excluded in url for excluded in excluded_urls
            ):
                coffee_urls.append(url)

        logger.info(f"Found {len(coffee_urls)} coffee product URLs out of {len(all_product_urls)} total products")
        return coffee_urls
