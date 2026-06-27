"""Drip Roasters scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="drip-roasters",
    display_name="Drip Roasters",
    roaster_name="Drip Roasters",
    website="https://driproasters.ch",
    description="Swiss specialty coffee roaster based in Bern, focused on carefully sourced single-origin coffees and small-batch roasting",
    requires_api_key=True,
    currency="CHF",
    country="Switzerland",
    status="available",
)
class DripRoastersScraper(ShopifyJsonScraper):
    """Scraper for Drip Roasters (driproasters.ch) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Drip Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Drip Roasters",
            base_url="https://driproasters.ch",
            products_json_urls=[
                "https://driproasters.ch/collections/coffee/products.json",
            ],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Exclude non-coffee products (subscriptions, gift cards, equipment,
        # sample packs, drip bags, ESE pods, B2B batch brew, etc.)
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
            "sample-pack",
            "drip-bags",
            "pods-pads",
            "batch-brew",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Drip Roasters product URLs to /products/<handle>.

        Shopify builds product URLs under each collection path; we strip the
        collection segment so all products share a single canonical URL.
        """
        if "/collections/" in url and "/products/" in url:
            handle = url.split("/products/", 1)[1]
            return f"{self.base_url}/products/{handle}"
        return url