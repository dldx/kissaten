"""September Coffee scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="september-coffee",
    display_name="September Coffee",
    roaster_name="September Coffee Company",
    website="https://september.coffee",
    description="Specialty coffee roaster based in Canada",
    requires_api_key=True,
    currency="CAD",
    country="Canada",
    status="available",
)
class SeptemberCoffeeScraper(BaseScraper):
    """Scraper for September Coffee (september.coffee) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize September Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="September Coffee Company",
            base_url="https://september.coffee",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
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
        return ["https://september.coffee/collections/coffee"]


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

        # Custom selectors for September Coffee (Shopify store)
        custom_selectors = [
            'a[href*="/products/"]',
            'a[href*="/products/"]',
            ".product-item a",
            ".grid-product__link",
            ".product-link",
        ]

        product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/products/", "/products/"],
            selectors=custom_selectors,
        )

        excluded_products = [
            "test-batch",  # Exclude test batches
        ]

        filtered_urls = []
        for url in product_urls:
            if url and isinstance(url, str) and not any(excluded in url.lower() for excluded in excluded_products):
                filtered_urls.append(url)

        return filtered_urls
