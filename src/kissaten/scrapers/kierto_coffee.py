"""Kierto Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="kierto-coffee",
    display_name="Kierto Coffee",
    roaster_name="Kierto Coffee",
    website="https://kierto.coffee",
    description="Australian specialty coffee roaster working notably light, with a "
    "curated range of experimental process lots (enzyme washed, thermal shock, co-ferments) "
    "and competition-style single origins.",
    requires_api_key=True,
    currency="AUD",
    country="Australia",
    status="available",
)
class KiertoCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Kierto Coffee (kierto.coffee) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        super().__init__(
            roaster_name="Kierto Coffee",
            base_url="https://kierto.coffee",
            products_json_urls=["https://kierto.coffee/collections/coffee/products.json"],
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

        # Exclude non-coffee products and accidental Shopify admin duplicates
        # ("-copy" handles).
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
            "ethiopia-alo-coffee-tri-up-sky-project-infinity-dark-room-washed-74158-copy",
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
