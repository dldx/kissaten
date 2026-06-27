"""ZEFF Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="zeff",
    display_name="ZEFF. Coffee",
    roaster_name="ZEFF",
    website="https://zeffcoffee.com",
    description="Swiss specialty coffee micro-roaster based in Wetzikon, born from a garage project and driven by meticulous sourcing and roasting to deliver intriguing, authentic coffee experiences",
    requires_api_key=True,
    currency="CHF",
    country="Switzerland",
    status="available",
)
class ZeffCoffeeScraper(ShopifyJsonScraper):
    """Scraper for ZEFF. Coffee (zeffcoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize ZEFF Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="ZEFF",
            base_url="https://zeffcoffee.com",
            products_json_urls=[
                "https://zeffcoffee.com/collections/all-products/products.json",
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

    def preprocess_product_url(self, url: str) -> str:
        """Standardize ZEFF product URLs to /products/<handle>.

        Shopify builds product URLs under each collection path; we strip the
        collection segment so all products share a single canonical URL.
        """
        if "/collections/" in url and "/products/" in url:
            handle = url.split("/products/", 1)[1]
            return f"{self.base_url}/products/{handle}"
        return url