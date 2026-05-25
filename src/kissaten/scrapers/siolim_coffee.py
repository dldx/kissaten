"""Siolim Coffee scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="siolim-coffee",
    display_name="Siolim Coffee",
    roaster_name="Siolim Coffee",
    website="https://www.siolim.coffee",
    description="Specialty coffee roaster based in India",
    requires_api_key=True,
    currency="INR",
    country="India",
    status="available",
)
class SiolimCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Siolim Coffee with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Siolim Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Siolim Coffee",
            base_url="https://www.siolim.coffee",
            products_json_urls=["https://www.siolim.coffee/collections/roasted-coffee/products.json"],
            use_optimized_mode=True,
            scrape_product_pages=True,
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
        self.exclude_slugs = ["cascara"]

    def preprocess_product_url(self, url: str) -> str:
        """Standardize URLs to direct /products/ format.

        Args:
            url: Original product URL

        Returns:
            Standardized URL: https://www.siolim.coffee/products/<handle>
        """
        import re

        # Remove collection segments to match target format
        return re.sub(r"/collections/[^/]+/", "/", url)
