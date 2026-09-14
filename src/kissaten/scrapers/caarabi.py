"""Caarabi Coffee Roasters scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="caarabi",
    display_name="Caarabi Coffee Roasters",
    roaster_name="Caarabi Coffee Roasters",
    website="https://caarabicoffee.com",
    description="New Delhi-based specialty coffee roaster sourcing single-origin Arabicas "
    "from Indian estates across Karnataka, Melkoduge, Baarbara, and Nagaland",
    requires_api_key=True,
    currency="INR",
    country="India",
    status="available",
)
class CaarabiCoffeeRoastersScraper(ShopifyJsonScraper):
    """Scraper for Caarabi Coffee Roasters (caarabicoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Caarabi Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Caarabi Coffee Roasters",
            base_url="https://caarabicoffee.com",
            products_json_urls=[
                "https://caarabicoffee.com/collections/shop-coffee-online/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Pin the home-market currency: Shopify Markets can serve geolocated
        # conversions to datacenter IPs, but every price on this store is INR.
        self.store_currency = "INR"
        self._currency_detected = True

        # The curated shop-coffee-online collection contains only coffee, but
        # keep an insurance list in case gear/gift items are ever added to it.
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
            "omakase",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def _canonicalize_url(self, url: str) -> str:
        # Canonical product pages are /products/<handle> (confirmed via
        # rel=canonical/og:url); collapse the collection segment so the URLs we
        # scrape match the site's real URL form.
        return re.sub(r"/collections/[^/]+/products/", "/products/", url)

    def preprocess_product_url(self, url: str) -> str:
        """Canonicalize collection-prefixed product URLs to ``/products/<handle>``."""
        return self._canonicalize_url(url)
