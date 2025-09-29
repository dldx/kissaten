"""Revel Coffee scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="revel-coffee",
    display_name="Revel Coffee",
    roaster_name="Revel Coffee",
    website="https://revelcoffee.com",
    description="Montana specialty coffee roaster offering single origins and blends",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="available",
)
class RevelCoffeeScraper(BaseScraper):
    """Scraper for Revel Coffee (revelcoffee.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Revel Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Revel Coffee",
            base_url="https://revelcoffee.com",
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
        return ["https://revelcoffee.com/coffee/"]


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
        """Extract product URLs from store page, only from main content.

        Args:
            store_url: URL of the store page

        Returns:
            List of product URLs
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        # Get all product URLs using the base class method first
        all_urls = self.extract_product_urls_from_soup(
            soup.find('main'),  # Only search within the main content
            url_path_patterns=["/"],  # Revel uses direct slug URLs
            selectors=[
                'a[href]',  # All links
                '.product-item a',
                '.product-link',
                'h3 a',  # Product title links
            ],
        )

        # Filter to only include URLs that look like coffee products
        # and exclude known non-product pages
        excluded_paths = [
            "/coffee/",  # Category page
            "/cart.php",
            "/contact",
            "/shipping",
            "/blog",
            "/merch/",
            "/pages.php",
            "/sitemap.php",
            "/subscription",
        ]

        filtered_urls = []
        for url in all_urls:
            # Skip if it contains excluded paths
            if any(excluded in url.lower() for excluded in excluded_paths):
                continue

            # Skip if it's the same as the store URL
            if url == store_url:
                continue

            # If it's a path under the domain and doesn't match exclusions, likely a product
            if (self.base_url in url and
                    url != self.base_url and
                    url != f"{self.base_url}/"):
                filtered_urls.append(url)

        return filtered_urls
