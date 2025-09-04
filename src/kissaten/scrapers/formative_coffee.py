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

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the store URL
        """
        return ["https://formative.coffee/collections/coffee"]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Formative Coffee store using AI extraction.

        Returns:
            List of CoffeeBean objects
        """
        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=self._extract_product_urls_from_store,
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
