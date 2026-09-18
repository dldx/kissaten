"""FUNK Coffee scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="funk-coffee",
    display_name="FUNK Coffee",
    roaster_name="FUNK Coffee",
    website="https://funk.coffee",
    description="Specialty coffee roaster based in Vancouver, BC, roasting playful, "
    "music-inspired single origins and blends",
    requires_api_key=True,
    currency="CAD",
    country="Canada",
    status="experimental",
)
class FunkCoffeeScraper(ShopifyJsonScraper):
    """Scraper for FUNK Coffee (funk.coffee) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize FUNK Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="FUNK Coffee",
            base_url="https://funk.coffee",
            products_json_urls=["https://funk.coffee/collections/coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude non-coffee products (subscriptions and brewing equipment).
        self.exclude_slugs = [
            "subscription",
            "dripper",
            "filters",
        ]

        # Pin the home-market currency: Shopify Markets can geo-convert prices
        # for datacenter IPs; cart.js from the home market reports CAD.
        self.store_currency = "CAD"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize product URLs to the canonical /products/<handle> form.

        The site's product sitemap uses the no-collection URL form.
        """
        return re.sub(r"/collections/[^/]+/products/", "/products/", url)
