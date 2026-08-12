"""Barista Culture scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="barista-culture",
    display_name="Barista Culture",
    roaster_name="Barista Culture",
    website="https://baristaculture.co.uk",
    description="Specialty coffee roaster and coffee shop based in Milton Keynes, "
    "partnered with the Blackened Sun Brewing Co micro-brewery.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class BaristaCultureScraper(ShopifyJsonScraper):
    """Scraper for Barista Culture (baristaculture.co.uk) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Barista Culture scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Barista Culture",
            base_url="https://www.baristaculture.co.uk",
            products_json_urls=["https://baristaculture.co.uk/products.json"],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude non-coffee products (subscriptions, gift cards, equipment, etc.)
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "sampler",
            "taster-pack",
            "apparel",
            "mug",
            "tumbler",
            "hoodie",
            "tshirt",
            "capsules",
            "pods",
            "cold-brew-cans",
            "easy-pour",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Barista Culture product URLs to the canonical www form.

        The homepage (https://baristaculture.co.uk) 301-redirects to the www
        host, and Shopify lists https://www.baristaculture.co.uk/products/<handle>
        as the canonical product URL. ShopifyJsonScraper builds product URLs from
        the non-www products.json base, so rewrite them to the canonical www form.
        """
        return url.replace("https://baristaculture.co.uk", "https://www.baristaculture.co.uk")
