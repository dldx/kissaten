"""Archers Coffee scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="archers-coffee",
    display_name="Archers Coffee",
    roaster_name="Archers Coffee",
    website="https://archerscoffee.com",
    description="Dubai-based specialty coffee roaster offering meticulously sourced and roasted "
    "single-origin coffees, pour-over selections, espresso blends, and bespoke blends",
    requires_api_key=True,
    currency="AED",
    country="United Arab Emirates",
    status="available",
)
class ArchersCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Archers Coffee using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Archers Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Archers Coffee",
            base_url="https://archerscoffee.com",
            products_json_urls=[
                "https://archerscoffee.com/collections/espresso-milk-coffees-2025/products.json",
                "https://archerscoffee.com/collections/pour-over-coffees-2025/products.json",
                "https://archerscoffee.com/collections/bespoke-blends-2025/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude non-coffee products (subscriptions, equipment, etc.)
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "accessory",
            "merchandise",
            "academy",
            "bundle",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def _canonicalize_url(self, url: str) -> str:
        # Canonical product pages are /products/<handle>; collapse the collection
        # segment so old /collections/<slug>/products/<handle> history entries match
        # the new canonical form (prevents re-scrape / false out-of-stock).
        return re.sub(r"/collections/[^/]+/products/", "/products/", url)

    def preprocess_product_url(self, url: str) -> str:
        """Canonicalize collection-prefixed product URLs to ``/products/<handle>``.

        A product listed in multiple collections is the same physical product,
        so collapsing the collection segment merges the same handle across
        collections (e.g. espresso-milk + pour-over) without merging distinct
        filter/espresso products (those keep different handles and are
        represented within one bean via ``roast_profile``).
        """
        return self._canonicalize_url(url)
