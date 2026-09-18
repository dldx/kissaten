"""Micrology Coffee Roasters scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="micrology",
    display_name="Micrology Coffee Roasters",
    roaster_name="Micrology Coffee Roasters",
    website="https://micrology.com.au",
    description="Australian specialty coffee roaster in Melbourne roasting single "
    "origins and blends for filter and espresso.",
    requires_api_key=True,
    currency="AUD",
    country="Australia",
    status="experimental",
)
class MicrologyScraper(ShopifyJsonScraper):
    """Scraper for Micrology Coffee Roasters (micrology.com.au) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Micrology Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Micrology Coffee Roasters",
            base_url="https://micrology.com.au",
            products_json_urls=["https://micrology.com.au/collections/coffee-beans/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=1.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The curated "All Coffee Beans" collection mixes in prepaid gift
        # subscriptions; sampler packs are kept and flagged for review
        # downstream instead.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Strip the collection segment to match Micrology's canonical product URLs.

        ShopifyJsonScraper builds product URLs as
        ``<products.json base>/products/<handle>``, which yields a
        ``/collections/coffee-beans/products/<handle>`` form. Micrology's
        canonical product pages are served at ``/products/<handle>``.
        """
        return re.sub(r"/collections/[^/]+/products/", "/products/", url)
