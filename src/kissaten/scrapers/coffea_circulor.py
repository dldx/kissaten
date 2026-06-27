"""Coffea Circulor scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="coffea-circulor",
    display_name="Coffea Circulor",
    roaster_name="Coffea Circulor",
    website="https://coffeacirculor.com",
    description="Specialty coffee roaster based in Gothemburg, Sweden, focused on producing, sourcing and roasting award-winning coffee since 2005",
    requires_api_key=True,
    currency="EUR",
    country="Sweden",
    status="available",
)
class CoffeaCirculorScraper(ShopifyJsonScraper):
    """Scraper for Coffea Circulor (coffeacirculor.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Coffea Circulor scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Coffea Circulor",
            base_url="https://coffeacirculor.com",
            products_json_urls=[
                "https://coffeacirculor.com/collections/coffee/products.json",
            ],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
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
