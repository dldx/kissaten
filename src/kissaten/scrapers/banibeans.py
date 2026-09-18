"""Banibeans scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="banibeans",
    display_name="Banibeans",
    roaster_name="Banibeans",
    website="https://banibeans.si",
    description="Slovenian specialty coffee roaster offering a small selection of single-origin "
    "filter coffees and the Fermentation Project tasting kit",
    requires_api_key=True,
    currency="EUR",
    country="Slovenia",
    status="experimental",
)
class BanibeansScraper(ShopifyJsonScraper):
    """Scraper for Banibeans (banibeans.si) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Banibeans scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Banibeans",
            base_url="https://banibeans.si",
            products_json_urls=["https://banibeans.si/collections/all/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Pin the home-market currency: Shopify Markets can serve geo-converted
        # prices depending on caller IP / Accept-Language, so runtime detection
        # is not trusted.
        self.store_currency = "EUR"
        self._currency_detected = True

        # Tiny catalogue: paper filters and a catering service sit alongside the
        # beans (which include the Fermentation Project tasting kit).
        self.exclude_slugs = [
            "paper-filters",
            "catering",
            "gift-card",
            "gift",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def _canonicalize_url(self, url: str) -> str:
        # Canonical product pages are /products/<handle> (collection-prefixed
        # URLs 301-redirect there).
        return re.sub(r"/collections/[^/]+/products/", "/products/", url)

    def preprocess_product_url(self, url: str) -> str:
        """Canonicalize collection-prefixed product URLs to ``/products/<handle>``."""
        return self._canonicalize_url(url)
