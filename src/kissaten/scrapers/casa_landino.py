"""Casa Landino scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="casa-landino",
    display_name="Casa Landino",
    roaster_name="Casa Landino",
    website="https://casalandino.com",
    description="Colombian specialty coffee roaster (Armenia, Quindío) offering farm-direct "
    "single origins from the Serie Maestros line plus the James Hoffmann Fermentation Project",
    requires_api_key=True,
    currency="COP",
    country="Colombia",
    status="experimental",
)
class CasaLandinoScraper(ShopifyJsonScraper):
    """Scraper for Casa Landino (casalandino.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Casa Landino scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Casa Landino",
            base_url="https://casalandino.com",
            products_json_urls=["https://casalandino.com/collections/cafes-latinos-especiales/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Pin the home-market currency (COP; Shopify reports COP with rate 1.0):
        # Shopify Markets can serve geo-converted prices depending on caller
        # IP / Accept-Language, so runtime detection is not trusted.
        self.store_currency = "COP"
        self._currency_detected = True

        # The "cafes-latinos-especiales" collection contains the coffees plus the
        # Fermentation Project kits/bundles; kits are kept (flagged for review
        # downstream). Only a gift-card safety net is needed.
        self.exclude_slugs = [
            "gift-card",
            "gift",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def _canonicalize_url(self, url: str) -> str:
        # Canonical product pages are /products/<handle> (the canonical link tag
        # points there even though the collection URL also serves 200).
        return re.sub(r"/collections/[^/]+/products/", "/products/", url)

    def preprocess_product_url(self, url: str) -> str:
        """Canonicalize collection-prefixed product URLs to ``/products/<handle>``."""
        return self._canonicalize_url(url)
