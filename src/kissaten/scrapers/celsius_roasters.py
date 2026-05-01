"""Celsius Roasters scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="celsius-roasters",
    display_name="Celsius Roasters",
    roaster_name="Celsius Roasters",
    website="https://celsius-roasters.fr",
    description="French specialty coffee roaster based in Lyon",
    requires_api_key=True,
    currency="EUR",
    country="France",
    status="available",
)
class CelsiusRoastersScraper(ShopifyJsonScraper):
    """Scraper for Celsius Roasters (celsius-roasters.fr) using Shopify products.json."""

    def preprocess_product_url(self, url: str) -> str:
        """Ensure product URLs use the fixed /en/products/handle format, removing collections."""
        if "/products/" in url:
            handle = url.split("/products/")[-1]
            return f"{self.base_url}/en/products/{handle}"
        return url

    def __init__(self, api_key: str | None = None):
        """Initialize Celsius Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Celsius Roasters",
            base_url="https://celsius-roasters.fr",
            products_json_urls=[
                "https://celsius-roasters.fr/en/collections/les-cafes/products.json",
            ],
            scrape_product_pages=True,
            use_optimized_mode=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        # Exclude common non-coffee products
        self.exclude_slugs = [
            "gift-card",
            "subscription",
            "workshop",
            "tasting",
            "equipment",
            "accessories",
        ]
