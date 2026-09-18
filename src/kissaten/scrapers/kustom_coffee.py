"""Kustom Coffee scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="kustom-coffee",
    display_name="Kustom Coffee",
    roaster_name="Kustom Coffee",
    website="https://kustomcoffee.com",
    description="US-based micro-roastery roasting very small batches of ethically sourced specialty coffee",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class KustomCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Kustom Coffee (kustomcoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Kustom Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Kustom Coffee",
            base_url="https://kustomcoffee.com",
            products_json_urls=[
                "https://kustomcoffee.com/collections/single-origin-coffees/products.json",
                "https://kustomcoffee.com/collections/coffee-blends-1/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # No exclusions needed: the coffee collections only hold beans plus the
        # Fermentation Project tasting kit (kept — flagged downstream).

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
