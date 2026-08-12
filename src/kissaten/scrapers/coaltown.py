"""Coaltown Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="coaltown",
    display_name="Coaltown Coffee",
    roaster_name="Coaltown",
    website="https://coaltowncoffee.co.uk",
    description="Welsh specialty coffee roaster based in Ammanford, Carmarthenshire, "
    "known for carefully sourced single origins and blends roasted in Wales",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class CoaltownScraper(ShopifyJsonScraper):
    """Scraper for Coaltown Coffee (coaltowncoffee.co.uk) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Coaltown scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Coaltown",
            base_url="https://coaltowncoffee.co.uk",
            products_json_urls=["https://coaltowncoffee.co.uk/collections/coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude non-coffee products (pods, gift bundles/boxes, subscriptions, etc.)
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
