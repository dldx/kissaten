"""Dorothea Coffee scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="dorothea-coffee",
    display_name="Dorothea Coffee",
    roaster_name="Dorothea Coffee",
    website="https://dorotheacoffee.com",
    description="Specialty coffee roaster focused on seasonal single origins and "
    "house blends with transparent sourcing",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class DorotheaCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Dorothea Coffee (dorotheacoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Dorothea Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Dorothea Coffee",
            base_url="https://dorotheacoffee.com",
            products_json_urls=["https://dorotheacoffee.com/collections/coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # No exclusions needed: the curated coffee collection only holds beans
        # plus the Fermentation Project tasting kit (kept — flagged downstream).

        # Pin the home-market currency: Shopify Markets can geo-convert prices
        # for datacenter IPs; cart.js from the home market reports USD.
        self.store_currency = "USD"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize product URLs to the canonical /products/<handle> form.

        The site's product sitemap uses the no-collection URL form.
        """
        return re.sub(r"/collections/[^/]+/products/", "/products/", url)
