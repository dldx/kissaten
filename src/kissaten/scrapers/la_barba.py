"""La Barba Coffee scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="la-barba",
    display_name="La Barba Coffee",
    roaster_name="La Barba Coffee",
    website="https://labarbacoffee.com",
    description="Utah-based specialty coffee roaster known for bright single origins and approachable espresso blends",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class LaBarbaScraper(ShopifyJsonScraper):
    """Scraper for La Barba Coffee (labarbacoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize La Barba Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="La Barba Coffee",
            base_url="https://labarbacoffee.com",
            products_json_urls=["https://labarbacoffee.com/collections/all-coffees/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude gift cards only; coffee sets (including the Fermentation
        # Project collection) are genuine coffee and kept.
        self.exclude_slugs = [
            "gift-card",
        ]

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
