"""Taller Café scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="taller-cafe",
    display_name="Taller Café",
    roaster_name="Taller Café",
    website="https://taller.cafe",
    description="Chilean specialty coffee roaster based in Valparaíso",
    requires_api_key=True,
    currency="CLP",
    country="Chile",
    status="available",
)
class TallerCafeScraper(BaseScraper):
    """Scraper for Taller Café (taller.cafe) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Taller Café scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Taller Café",
            base_url="https://taller.cafe",
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
        return ["https://taller.cafe/collections/cafe-en-grano?sort_by=title-ascending"]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Taller Café using AI extraction.

        Returns:
            List of CoffeeBean objects
        """
        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=self._extract_product_urls_from_store,
            ai_extractor=self.ai_extractor,
            use_playwright=False,
            translate_to_english=True,  # Site is in Spanish
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

        # Use the new base class method with URL patterns for Shopify stores
        return self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/products/", "/collections/cafe-en-grano/products/"],
            selectors=[
                # Common Shopify product link selectors
                'a[href*="/products/"]',
                'a[href*="/collections/cafe-en-grano/products/"]',
                '.product-item a',
                '.product-link',
                '.grid-product__link',
                '.card-wrapper a',
            ],
        )
