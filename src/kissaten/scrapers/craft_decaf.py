"""Craft Decaf scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="craft-decaf",
    display_name="Craft Decaf",
    roaster_name="Craft Decaf",
    website="https://craftdecaf.com",
    description="UK-based specialty roaster dedicated exclusively to high-quality "
    "decaffeinated coffees from a range of origins and processes",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="experimental",
)
class CraftDecafScraper(ShopifyJsonScraper):
    """Scraper for Craft Decaf (craftdecaf.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Craft Decaf scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Craft Decaf",
            base_url="https://craftdecaf.com",
            products_json_urls=["https://craftdecaf.com/collections/all-products/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude non-coffee products (subscriptions, gift cards, equipment, etc.)
        self.exclude_slugs = [
            "subscription",
        ]

        # Pin the home-market currency: Shopify Markets can geo-convert prices
        # for datacenter IPs; cart.js from the home market reports GBP.
        self.store_currency = "GBP"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize product URLs to the canonical /products/<handle> form.

        The site's product sitemap uses the no-collection URL form.
        """
        return re.sub(r"/collections/[^/]+/products/", "/products/", url)
