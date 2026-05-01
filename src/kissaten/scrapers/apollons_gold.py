"""Apollon's Gold scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="apollons-gold",
    display_name="Apollon's Gold",
    roaster_name="Apollon's Gold",
    website="https://shop.apollons-gold.com",
    description="Japanese specialty coffee roaster based in Tokyo, known for high-quality "
    "single origin coffees and exceptional geisha varieties",
    requires_api_key=True,
    currency="GBP",
    country="Japan",
    status="available",
)
class ApollonsGoldScraper(ShopifyJsonScraper):
    """Scraper for Apollon's Gold (shop.apollons-gold.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Apollon's Gold scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Apollon's Gold",
            base_url="https://shop.apollons-gold.com",
            products_json_urls=["https://shop.apollons-gold.com/collections/frontpage/products.json"],
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
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
