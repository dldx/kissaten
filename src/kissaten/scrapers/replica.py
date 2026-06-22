"""Replica Roasters scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="replica",
    display_name="Replica",
    roaster_name="Replica",
    website="https://replicaroasters.com",
    description="Belgian specialty coffee roaster based in Leuven, focused on carefully sourced "
    "single origin coffees and seasonal selections",
    requires_api_key=True,
    currency="EUR",
    country="Belgium",
    status="available",
)
class ReplicaScraper(ShopifyJsonScraper):
    """Scraper for Replica Roasters (replicaroasters.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Replica Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Replica",
            base_url="https://replicaroasters.com",
            products_json_urls=["https://replicaroasters.com/products.json"],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

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
            "test-roast",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)