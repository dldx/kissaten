"""Monastery Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="monastery-coffee",
    display_name="Monastery Coffee",
    roaster_name="Monastery Coffee",
    website="https://monasterycoffee.com.au",
    description="South Australian specialty coffee roaster producing nicely developed "
    "light roasts with a rotating range of current single-origin offerings and blends.",
    requires_api_key=True,
    currency="AUD",
    country="Australia",
    status="available",
)
class MonasteryCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Monastery Coffee (monasterycoffee.com.au) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        super().__init__(
            roaster_name="Monastery Coffee",
            base_url="https://monasterycoffee.com.au",
            products_json_urls=["https://monasterycoffee.com.au/collections/current-offerings/products.json"],
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
            "books",
            "chocolate",
            "tea",
            "drinks",
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
