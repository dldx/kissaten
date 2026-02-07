"""Formative Coffee scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="formative",
    display_name="Formative Coffee",
    roaster_name="Formative Coffee",
    website="https://formative.coffee",
    description="UK-based specialty coffee roaster with focus on exceptional single origins",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class FormativeCoffeeScraper(BaseScraper):
    """Scraper for Formative Coffee (formative.coffee) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Formative Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Formative Coffee",
            base_url="https://formative.coffee",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
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
        return ["https://formative.coffee/collections/coffee"]


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
            use_optimized_mode=True
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

        # Custom selectors for Formative Coffee (Shopify-based)
        custom_selectors = [
            'a[href*="/products/"]',
            'a[href*="/collections/coffee/products/"]',
            '.product-item a',
            '.grid__item a',
            'a.product-link',
        ]

        return self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/products/", "/collections/coffee/products/"],
            selectors=custom_selectors,
        )
