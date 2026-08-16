"""Harmony Coffee scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="harmony",
    display_name="Harmony",
    roaster_name="Harmony",
    website="https://harmonycoffee.co.uk",
    description="UK specialty coffee roaster sourcing exceptional single origins and "
    "masterpiece experimental lots with a focus on transparent, high-quality coffee",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class HarmonyCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Harmony Coffee (harmonycoffee.co.uk) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Harmony Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Harmony",
            base_url="https://harmonycoffee.co.uk",
            products_json_urls=["https://www.harmonycoffee.co.uk/collections/our-coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Exclude non-coffee products: gift cards, subscriptions (including decaf
        # and office/monthly variants), and the Felicita Parallel coffee scale.
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
            "cold-brew-cans",
            "easy-pour",
            # Harmony-specific non-coffee / equipment handles
            "felicita",  # Felicita Parallel coffee scale
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Canonicalize Harmony Coffee product URLs.

        Strips any collection segment so URLs match the site's real product
        pages, which are simply /products/{handle} (no collection path).
        """
        return re.sub(r"/collections/[^/]+/products/", "/products/", url)
