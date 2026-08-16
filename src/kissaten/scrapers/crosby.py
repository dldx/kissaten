"""Crosby Coffee scraper implementation using Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="crosby",
    display_name="Crosby",
    roaster_name="Crosby",
    website="https://crosbycoffee.co.uk",
    description="Specialty coffee roaster based in Liverpool, UK, offering single origins "
    "and signature blends with detailed tasting notes and cup scores",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class CrosbyScraper(ShopifyJsonScraper):
    """Scraper for Crosby (crosbycoffee.co.uk) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Crosby Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Crosby",
            base_url="https://crosbycoffee.co.uk",
            products_json_urls=["https://crosbycoffee.co.uk/collections/coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude non-coffee products (sample boxes, gift bags, storage, etc.)
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "personalised-coffee-bag",
            "canister",
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
