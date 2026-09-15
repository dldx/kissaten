"""Good Cup scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="good-cup",
    display_name="Good Cup",
    roaster_name="Good Cup",
    website="https://goodcup.ph",
    description="Manila-based specialty coffee roaster showcasing Philippine and "
    "international single origins alongside signature blends",
    requires_api_key=True,
    currency="PHP",
    country="Philippines",
    status="experimental",
)
class GoodCupScraper(ShopifyJsonScraper):
    """Scraper for Good Cup (goodcup.ph) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Good Cup scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Good Cup",
            base_url="https://goodcup.ph",
            products_json_urls=["https://goodcup.ph/collections/coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # No exclusions needed: the curated coffee collection only holds beans
        # (classes, cups, equipment, merch etc. live in separate collections).

        # Pin the home-market currency: Shopify Markets can geo-convert prices
        # for datacenter IPs; cart.js from the home market reports PHP.
        self.store_currency = "PHP"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize product URLs to the canonical /products/<handle> form.

        The site's product sitemap uses the no-collection URL form.
        """
        return re.sub(r"/collections/[^/]+/products/", "/products/", url)
