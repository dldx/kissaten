"""Garage Roasters scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="garage-roasters",
    display_name="Garage Roasters",
    roaster_name="Garage Roasters",
    website="https://garageroasters.com.au",
    description="Australian specialty coffee roaster offering a wide range of "
    "single origins, blends and limited-edition roasts",
    requires_api_key=True,
    currency="AUD",
    country="Australia",
    status="experimental",
)
class GarageRoastersScraper(ShopifyJsonScraper):
    """Scraper for Garage Roasters (garageroasters.com.au) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Garage Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Garage Roasters",
            base_url="https://garageroasters.com.au",
            # Bean coverage is fragmented across many curated collections
            # (single-origins, espresso-roasts, premium-blends, ...), so the
            # complete catalogue collection is used with slug exclusions.
            products_json_urls=["https://garageroasters.com.au/collections/all/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude genuine equipment and non-coffee items only. Sample packs and
        # the Fermentation Project tasting kit are kept (flagged downstream).
        self.exclude_slugs = [
            "coffee-machine",
            "grinder",
            "gift-voucher",
        ]

        # Pin the home-market currency: Shopify Markets can geo-convert prices
        # for datacenter IPs; cart.js from the home market reports AUD.
        self.store_currency = "AUD"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize product URLs to the canonical /products/<handle> form.

        The site's product sitemap uses the no-collection URL form.
        """
        return re.sub(r"/collections/[^/]+/products/", "/products/", url)
