"""Skylark Coffee scraper.

UK-based specialty coffee roaster from Brighton, donating 100% of proceeds to charity.
Known for their ethical sourcing and detailed origin stories.
"""

import logging
from pathlib import Path

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="skylark-coffee",
    display_name="Skylark Coffee",
    roaster_name="Skylark Coffee",
    website="https://skylark.coffee",
    description="UK specialty coffee roaster donating 100% of proceeds to charity, "
    "known for ethical sourcing and detailed origin stories",
    requires_api_key=True,  # Using AI extraction for best results
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class SkylarkCoffeeScraper(BaseScraper):
    """Scraper for Skylark Coffee."""

    def __init__(self, api_key: str | None = None):
        """Initialize the scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Skylark Coffee",
            base_url="https://skylark.coffee",
            rate_limit_delay=1.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the store URL
        """
        return [
            f"https://skylark.coffee/collections/coffee?page={page}"
            for page in range(1, 7)
        ]


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
            use_playwright=False,
        )

    def _get_excluded_url_path_patterns(self) -> list[str]:
        return super()._get_excluded_url_path_patterns() + ["four-pack-sampler-mixed", "12-days-of-christmas"]

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

        # Custom selectors for Skylark Coffee (Shopify site)
        custom_selectors = [
            'a[href*="/collections/coffee/products/"]',
            'a[href*="/products/"]',
            ".product-item a",
            ".product-link",
            ".product-title a",
            "h3 a",  # Common pattern for product titles
        ]

        # Extract all product URLs using the base class method
        all_product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/collections/coffee/products/", "/products/"],
            selectors=custom_selectors,
        )

        # Filter coffee products using base class method
        coffee_urls = []
        for url in all_product_urls:
            if self.is_coffee_product_url(url, required_path_patterns=["/products/"]):
                coffee_urls.append(url)

        logger.info(f"Found {len(coffee_urls)} coffee product URLs out of {len(all_product_urls)} total products")
        return coffee_urls
