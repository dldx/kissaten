"""Cartwheel Coffee scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="cartwheel",
    display_name="Cartwheel Coffee",
    roaster_name="Cartwheel Coffee",
    website="https://cartwheelcoffee.com",
    description="UK-based specialty coffee roaster",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class CartwheelCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Cartwheel Coffee using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Cartwheel Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Cartwheel Coffee",
            base_url="https://cartwheelcoffee.com",
            products_json_urls=[
                "https://cartwheelcoffee.com/collections/coffee/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude non-coffee products (subscriptions, equipment, gifts, etc.)
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "giftcard",
            "workshop",
            "course",
            "equipment",
            "accessory",
            "grinder",
            "kettle",
            "brewer",
            "filter-paper",
            "filter",
            "merch",
            "tee",
            "tote",
            "apparel",
            "hot-chocolate",
            "chai",
            "tea",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Normalize product URLs to ``/products/<handle>`` by stripping collection segments."""
        return re.sub(r"^(https?://[^/]+)/collections/[^/]+/", r"\1/", url)
