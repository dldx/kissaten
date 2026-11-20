"""Anamorphic Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="anamorphic-coffee",
    display_name="Anamorphic Coffee",
    roaster_name="Anamorphic Coffee",
    website="https://anamorphiccoffee.com",
    description="Sydney-based specialty coffee roaster known for roasting very light, "
    "ultra-light Nordic-style profiles that stand out among Australian roasters.",
    requires_api_key=True,
    currency="AUD",
    country="Australia",
    status="available",
)
class AnamorphicCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Anamorphic Coffee (anamorphiccoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        super().__init__(
            roaster_name="Anamorphic Coffee",
            base_url="https://anamorphiccoffee.com",
            products_json_urls=["https://anamorphiccoffee.com/collections/coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Pin the home currency so a datacenter IP can't get AUD converted to
        # another market currency via Shopify Markets geolocation.
        self.store_currency = "AUD"
        self._currency_detected = True

        # Exclude non-coffee products (merch, subscriptions, gift cards, equipment, etc.)
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "merch",
            "sampler",
            "taster-pack",
            "apparel",
            "mug",
            "tumbler",
            "hoodie",
            "tshirt",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize product URLs to the site's canonical /products/<handle> form."""
        if "/products/" in url:
            handle = url.split("/products/")[-1]
            return f"{self.base_url}/products/{handle}"
        return url
