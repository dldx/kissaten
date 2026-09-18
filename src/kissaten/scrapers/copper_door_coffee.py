"""Copper Door Coffee scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="copper-door-coffee",
    display_name="Copper Door Coffee",
    roaster_name="Copper Door Coffee",
    website="https://copperdoorcoffee.com",
    description="Denver-based specialty coffee roaster offering single origins, blends, instant "
    "packets and the Fermentation Project kit",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class CopperDoorCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Copper Door Coffee (copperdoorcoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Copper Door Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Copper Door Coffee",
            base_url="https://copperdoorcoffee.com",
            products_json_urls=["https://copperdoorcoffee.com/collections/coffee/products.json"],
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
        # safety net for subscriptions/gift cards/drinkware.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "mug",
            "tumbler",
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
