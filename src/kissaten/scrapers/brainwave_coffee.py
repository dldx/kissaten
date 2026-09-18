"""Brainwave Coffee Roasters scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="brainwave-coffee",
    display_name="Brainwave Coffee Roasters",
    roaster_name="Brainwave Coffee Roasters",
    website="https://brainwaveroasters.com",
    description="Specialty coffee roaster focused on experimental Colombian lots (gesha, co-ferments, "
    "rarities) plus the James Hoffmann Fermentation Project",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class BrainwaveCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Brainwave Coffee Roasters (brainwaveroasters.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Brainwave Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Brainwave Coffee Roasters",
            base_url="https://brainwaveroasters.com",
            products_json_urls=["https://brainwaveroasters.com/collections/all/products.json"],
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
        self.store_currency = "USD"
        self._currency_detected = True

        # Tiny catalogue: only the subscription needs excluding.
        self.exclude_slugs = [
            "subscription",
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
