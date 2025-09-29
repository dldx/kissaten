"""Hermanos Coffee Roasters scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="hermanos",
    display_name="Hermanos Coffee Roasters",
    roaster_name="Hermanos Coffee Roasters",
    website="https://hermanoscoffeeroasters.com",
    description="UK-based specialty coffee roaster known for Colombian coffees",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class HermanosCoffeeRoastersScraper(BaseScraper):
    """Scraper for Hermanos Coffee Roasters (hermanoscoffeeroasters.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Hermanos Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Hermanos Coffee Roasters",
            base_url="https://hermanoscoffeeroasters.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the store URLs - includes multiple pages
        """
        return [
            "https://hermanoscoffeeroasters.com/collections/colombian-specialty-coffee?filter.v.availability=1",
            "https://hermanoscoffeeroasters.com/collections/colombian-specialty-coffee?page=2&filter.v.availability=1",
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

        custom_selectors = [
            'a[href*="/products/"]',
        ]

        product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/products/"],
            selectors=custom_selectors,
        )

        # Filter out non-coffee products
        filtered_urls = []
        excluded_patterns = ["-pods", "-capsules", "tasting-kit", "-gift-set"]
        for url in product_urls:
            if (
                url
                and isinstance(url, str)
                and self.is_coffee_product_url(url, required_path_patterns=["/products/"])
                and not any(pattern in url for pattern in excluded_patterns)
            ):
                filtered_urls.append(url.split("?")[0])

        return list(set(filtered_urls))
