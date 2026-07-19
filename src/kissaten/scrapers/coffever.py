"""Coffever scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="coffever",
    display_name="Coffever",
    roaster_name="Coffever",
    website="https://coffever.co.uk",
    description="Specialty coffee roaster from Hong Kong now based in Bath, United Kingdom.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class CoffeverScraper(ShopifyJsonScraper):
    """Scraper for Coffever (coffever.co.uk) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Coffever scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Coffever",
            base_url="https://coffever.co.uk",
            products_json_urls=["https://coffever.co.uk/collections/all/products.json"],
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
        """Strip the /collections/all segment so URLs match the canonical product format.

        Coffever's canonical product URLs are https://coffever.co.uk/products/<handle>,
        but ShopifyJsonScraper builds them from the products.json base, inserting
        /collections/all. Normalize to the canonical form.
        """
        return url.replace("/collections/all/products/", "/products/")
