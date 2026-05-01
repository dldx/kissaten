"""Goût and Co Coffee scraper implementation with AI-powered extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="gout-and-co",
    display_name="Goût and Co",
    roaster_name="Goût and Co",
    website="https://www.goutandco.com",
    description="Chengdu-based specialty coffee roaster",
    requires_api_key=True,
    currency="GBP",
    country="China",
    status="available",
)
class GoutAndCoScraper(ShopifyJsonScraper):
    """Scraper for Goût and Co using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Goût and Co scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Goût and Co",
            base_url="https://www.goutandco.com",
            products_json_urls=[
                "https://goutandco.com/collections/all/products.json",
            ],
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
            scrape_product_pages=True,
            use_optimized_mode=True,
        )

        # Exclude non-coffee products
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "accessory",
            "merchandise",
            "-year-drop",
            "collaboration",
            "cap",
            "-cup",
            "limited-product",
        ]

        # Initialize AI extractor
        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Goût and Co URLs by removing collection segments."""
        if "/collections/" in url and "/products/" in url:
            try:
                handle = url.split("/products/")[-1].split("?")[0]
                return f"{self.base_url}/products/{handle}"
            except Exception:
                return url
        return url
