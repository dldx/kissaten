"""NORD scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="nord-coffee",
    display_name="NORD",
    roaster_name="NORD",
    website="https://nord.coffee",
    description="Sydney-based specialty coffee roaster focused on unique and exotic "
    "coffees — a small, rotating list of current-release single origins roasted light "
    "and shipped worldwide.",
    requires_api_key=True,
    currency="AUD",
    country="Australia",
    status="available",
)
class NordCoffeeScraper(ShopifyJsonScraper):
    """Scraper for NORD (nord.coffee) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        super().__init__(
            roaster_name="NORD",
            base_url="https://nord.coffee",
            products_json_urls=["https://nord.coffee/collections/frontpage/products.json"],
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
