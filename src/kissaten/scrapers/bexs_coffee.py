"""Bex's Coffee scraper implementation with Shopify JSON extraction.

Bex's Coffee (formerly HUD Coffee Co.) runs their bean shop on Shopify at
bexscoffee.com. The curated /collections/coffee collection contains only
coffee beans (gift cards and syrups live in their own collections), so we
target that products.json endpoint.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="bexs-coffee",
    display_name="Bex's Coffee",
    roaster_name="Bex's Coffee",
    website="https://bexscoffee.com",
    description="British coffee roaster (formerly HUD Coffee Co.) based in the UK, "
    "offering a range of single origin and blended coffees with multiple "
    "grind options and roast levels.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class BexsCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Bex's Coffee (bexscoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Bex's Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Bex's Coffee",
            base_url="https://bexscoffee.com",
            products_json_urls=["https://bexscoffee.com/collections/coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Pin the store currency to GBP. Bex's serves proper GBP from a
        # home-market curl, but the datacenter curl_cffi client could receive
        # geolocated/converted prices (Shopify Markets), so pin it.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Curated coffee collection only carries beans, but guard against any
        # non-coffee item that might slip in (subscription, gift card, etc.).
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
            "syrup",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
