"""Scraper for Artisan Roast Chile coffee roaster.

Artisan Roast is a Chilean specialty coffee roaster focused on circular coffee practices.
They offer single origins and blends with Chilean Peso pricing.
"""

import logging

from bs4 import BeautifulSoup
from pydantic import HttpUrl

from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="artisan-roast-cl",
    display_name="Artisan Roast Chile",
    roaster_name="Artisan Roast Chile",
    website="https://shop.artisanroast.cl",
    description="Chilean specialty coffee roaster focused on circular coffee practices",
    requires_api_key=True,  # Use AI extraction for this Spanish-language site
    currency="CLP",  # Chilean Peso
    country="Chile",
    status="available"
)
class ArtisanRoastScraper(BaseScraper):
    """Scraper for Artisan Roast Chile coffee roaster."""

    def __init__(self, api_key: str | None = None):
        super().__init__(
            roaster_name="Artisan Roast Chile",
            base_url="https://shop.artisanroast.cl",
            rate_limit_delay=1.0,
            max_retries=3,
            timeout=30.0
        )

        # Initialize AI extractor for this Spanish-language site
        self.ai_extractor = None
        try:
            from ..ai import CoffeeDataExtractor
            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
        except ImportError:
            logger.warning("AI extractor not available - falling back to traditional extraction")

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape."""
        return [
            "https://shop.artisanroast.cl/collections/origenes",  # Single origins
            "https://shop.artisanroast.cl/collections/blends",    # Blends
        ]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Artisan Roast Chile."""
        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=self._extract_product_urls_from_store,
            ai_extractor=self.ai_extractor,
            use_playwright=False,  # Standard Shopify site, no JS needed
            translate_to_english=True,  # Translate Spanish to English for AI extraction
        )


    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from store page."""
        soup = await self.fetch_page(store_url, use_playwright=False)
        if not soup:
            return []

        # Use base class method with Shopify-specific patterns
        return self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/collections/"],
            selectors=[
                'a[href*="/collections/origenes/products/"]',  # Standard Shopify product links
                'a[href*="/collections/blends/products/"]',  # Standard Shopify product links
                '.product-item a',        # Common product item links
                '.grid-product__link',    # Shopify grid layout
                'h4 a',                   # Product title links (seen in their HTML)
            ]
        )