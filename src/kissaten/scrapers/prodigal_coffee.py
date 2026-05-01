"""Prodigal Coffee scraper implementation with AI-powered extraction."""

import logging

from bs4 import BeautifulSoup

from ..schemas import CoffeeBean
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="prodigal-coffee",
    display_name="Prodigal Coffee",
    roaster_name="Prodigal Coffee",
    website="https://getprodigal.com",
    description="US specialty coffee roaster offering single origins and blends",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="available",
)
class ProdigalCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Prodigal Coffee using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Prodigal Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Prodigal Coffee",
            base_url="https://getprodigal.com",
            products_json_urls=[
                "https://getprodigal.com/collections/roasted-coffee/products.json",
            ],
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Exclude non-coffee products
        self.exclude_slugs = [
            "subscription",
            "sampler",
            "box-set",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "accessory",
            "merchandise",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Prodigal Coffee URLs by removing collection segments."""
        if "/collections/" in url and "/products/" in url:
            try:
                handle = url.split("/products/")[-1].split("?")[0]
                return f"{self.base_url}/products/{handle}"
            except Exception:
                return url
        return url
