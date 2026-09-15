"""Common Time Coffee scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="common-time-coffee",
    display_name="Common Time Coffee",
    roaster_name="Common Time Coffee",
    website="https://commontimecoffee.com",
    description="Atlanta-based specialty coffee roaster offering single origins, archived lots and "
    "the Fermentation Project tasting set",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class CommonTimeCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Common Time Coffee (commontimecoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Common Time Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Common Time Coffee",
            base_url="https://commontimecoffee.com",
            products_json_urls=["https://commontimecoffee.com/collections/coffee/products.json"],
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

        # The curated "coffee" collection already contains only beans; keep a
        # minimal safety net (the store also sells brewing gear/subscriptions).
        self.exclude_slugs = [
            "subscription",
            "membership",
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
