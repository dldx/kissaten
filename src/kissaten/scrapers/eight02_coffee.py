"""802 Coffee scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="802-coffee",
    display_name="802 Coffee",
    roaster_name="802 Coffee",
    website="https://802coffee.com",
    description="Vermont-based specialty coffee roaster offering single origins, blends and decafs "
    "plus the James Hoffmann Fermentation Project tasting kit",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class Eight02CoffeeScraper(ShopifyJsonScraper):
    """Scraper for 802 Coffee (802coffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize 802 Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="802 Coffee",
            base_url="https://802coffee.com",
            products_json_urls=["https://802coffee.com/collections/coffees/products.json"],
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

        # The curated "coffees" collection already contains only beans; keep a
        # minimal safety net for anything that drifts in.
        self.exclude_slugs = [
            "subscription",
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
