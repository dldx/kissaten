"""Extract Coffee scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="extract",
    display_name="Extract Coffee",
    roaster_name="Extract Coffee Roasters",
    website="https://extractcoffee.co.uk",
    description="UK-based specialty coffee roaster focusing on single origin and seasonal coffees",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class ExtractCoffeeScraper(BaseScraper):
    """Scraper for Extract Coffee (extractcoffee.co.uk) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Extract Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Extract Coffee Roasters",
            base_url="https://extractcoffee.co.uk",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the store URLs
        """
        return [
            "https://extractcoffee.co.uk/shop/coffee/single-origin/",
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

        # Custom selectors for Extract Coffee based on the structure observed
        custom_selectors = [
            'a[href*="/coffee/"]',
            'a[href*="/shop/"]',
            'a[href*="seasonal-filter"]',
            'a[href*="espresso"]',
            'a[href*="filter"]',
        ]

        product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/coffee/", "/shop/"],
            selectors=custom_selectors,
        )

        excluded_products = ["coffee-pods"]
        filtered_urls = [url for url in product_urls if not any(excl in url for excl in excluded_products)]
        return filtered_urls
