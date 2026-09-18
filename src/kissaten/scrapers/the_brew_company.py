"""The Brew Company scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="the-brew-company",
    display_name="The Brew Company",
    roaster_name="The Brew Company",
    website="https://brew-company.com",
    description="Danish specialty coffee company (Middelfart) offering single-origin whole beans, "
    "espresso blends and the Fermentation Project kit, alongside its patented Coffeebrewer",
    requires_api_key=True,
    currency="EUR",
    country="Denmark",
    status="experimental",
)
class TheBrewCompanyScraper(ShopifyJsonScraper):
    """Scraper for The Brew Company (brew-company.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize The Brew Company scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="The Brew Company",
            base_url="https://brew-company.com",
            products_json_urls=["https://brew-company.com/collections/coffee-beans/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Pin the store currency (the .com store sells in EUR; Shopify reports
        # EUR with rate 1.0). Pinning avoids Shopify Markets geo-conversion.
        self.store_currency = "EUR"
        self._currency_detected = True

        # The curated "coffee-beans" collection already contains only beans; keep
        # a minimal safety net. Coffeebrewer devices (brewer name category) and
        # teabrewers/grinders are excluded by the base name checks if they ever
        # drift into the collection.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "teabrewer",
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
