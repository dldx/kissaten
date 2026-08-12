"""Fidela Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="fidela",
    display_name="Fidela",
    roaster_name="Fidela",
    website="https://fidelacoffee.com",
    description="UK specialty coffee roaster sourcing exceptional single origin "
    "coffees from Colombia with transparency and care",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class FidelaScraper(ShopifyJsonScraper):
    """Scraper for Fidela (fidelacoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Fidela Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Fidela",
            base_url="https://fidelacoffee.com",
            products_json_urls=["https://fidelacoffee.com/collections/coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude non-coffee products (subscriptions, gift cards, sample packs,
        # gift bundles, equipment, etc.)
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
            "sample-pack",
            "bundle",
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
