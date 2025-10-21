"""Kaffeelix scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="kaffeelix",
    display_name="Kaffeelix",
    roaster_name="Kaffeelix",
    website="https://kaffeelix.at",
    description="Specialty coffee roaster based in Austria",
    requires_api_key=True,
    currency="EUR",
    country="Austria",
    status="available",
)
class KaffeelixScraper(BaseScraper):
    """Scraper for Kaffeelix with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Kaffeelix scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Kaffeelix",
            base_url="https://kaffeelix.at",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the coffee category URL
        """
        return [
            "https://kaffeelix.at/en/collections/world-of-coffee",
            "https://kaffeelix.at/en/collections/espresso",
            "https://kaffeelix.at/en/collections/espresso?page=2",
            "https://kaffeelix.at/en/collections/filterkaffee",
            "https://kaffeelix.at/en/collections/filterkaffee?page=2",
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

        # Create a function that returns the product URLs for the AI extraction
        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
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

        # Extract all product URLs using the base class method
        all_product_url_el = soup.select('a.product-card-link[href*="/products/"]')
        all_product_urls = []
        for el in all_product_url_el:
            if "Sold Out" not in el.parent.parent.text and el["href"] not in all_product_urls:
                all_product_urls.append(el["href"])

        excluded_pattern = ["brew-bag"]

        # Filter coffee products using base class method
        coffee_urls = []
        for url in all_product_urls:
            if self.is_coffee_product_url(url, required_path_patterns=["/products/"]) and not any(
                pattern in url for pattern in excluded_pattern
            ):
                coffee_urls.append(f"{self.base_url}{url}")

        logger.info(f"Found {len(coffee_urls)} coffee product URLs out of {len(all_product_urls)} total products")
        return coffee_urls
