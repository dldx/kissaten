"""Bjorn (Björn Speciality Coffee) scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="bjorn",
    display_name="Bjorn",
    roaster_name="Bjorn",
    website="https://bjornbeans.co.uk",
    description="Björn Speciality Coffee (formerly Yellow B Roasters, rebranded Oct 2025) "
    "is a UK specialty coffee roaster based in London, known for single origins, blends "
    "and decaf coffees.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class BjornScraper(ShopifyJsonScraper):
    """Scraper for Bjorn (bjornbeans.co.uk) using Shopify products.json.

    Uses the curated ``/collections/all-coffee`` collection which covers both
    single origins and house blends (avoiding double counting). Extracts from
    the rich product ``body_html`` in JSON-only mode (no product page fetch).
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Bjorn scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Bjorn",
            base_url="https://bjornbeans.co.uk",
            products_json_urls=["https://bjornbeans.co.uk/collections/all-coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=1.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Bjorn is a UK roaster priced in GBP. Pin the store currency so any
        # geo-localized presentment currency cannot override it during
        # extraction (see shopify_base._scrape_new_products).
        self.store_currency = "GBP"
        self._currency_detected = True

        # Exclude non-coffee products. The all-coffee collection is already
        # curated, but keep a defensive exclude list for any stray equipment /
        # liqueur / gift items that might appear in the feed.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "giftcard",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "merch",
            "liqueur",
            "mug",
            "tumbler",
            "apparel",
            "capsules",
            "pods",
            "cold-brew-cans",
            "easy-pour",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Strip the collection segment from product URLs.

        Bjorn's canonical product pages are ``/products/<handle>`` (no
        collection prefix), so remove the ``/collections/<name>/`` added by the
        Shopify base from the all-coffee products.json URLs.
        """
        return re.sub(r"/collections/[^/]+/products/", "/products/", url)
