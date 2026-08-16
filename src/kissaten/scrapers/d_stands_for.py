"""D Stands For scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="d-stands-for",
    display_name="D Stands For",
    roaster_name="D Stands For",
    website="https://decaf.at",
    description="Vienna-based specialty coffee roaster focused exclusively on high-quality decaf coffees from around the world",
    requires_api_key=True,
    currency="EUR",
    country="Austria",
    status="available",
)
class DStandsForScraper(ShopifyJsonScraper):
    """Scraper for D Stands For (decaf.at) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize D Stands For scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="D Stands For",
            base_url="https://decaf.at",
            products_json_urls=["https://decaf.at/en/products.json"],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude non-coffee products (subscriptions, gift cards, equipment, apparel, etc.)
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "apparel",
            "mug",
            "tumbler",
            "hoodie",
            "tshirt",
            "capsules",
            "pods",
            "cold-brew-cans",
            "easy-pour",
            "collection",
            "soap",
            "dripper",
            "mesh-bag",
            "t90",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
