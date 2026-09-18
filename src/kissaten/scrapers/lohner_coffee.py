"""Lohner Coffee scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="lohner-coffee",
    display_name="Lohner Coffee",
    roaster_name="Lohner Coffee",
    website="https://lohnercoffee.com",
    description="US specialty coffee roaster focused on single-origin lots from "
    "Colombia and Latin America, home of the James Hoffmann Fermentation Project kit.",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class LohnerCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Lohner Coffee (lohnercoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Lohner Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Lohner Coffee",
            base_url="https://lohnercoffee.com",
            products_json_urls=["https://lohnercoffee.com/collections/all/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=1.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Exclude non-coffee products (the store has no curated coffee
        # collection; /collections/all only mixes in three merch items).
        self.exclude_slugs = [
            "gift-card",
            "5-panel-hat",
            "hoodie",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Strip the collection segment to match Lohner's canonical product URLs.

        ShopifyJsonScraper builds product URLs as
        ``<products.json base>/products/<handle>``, which yields a
        ``/collections/all/products/<handle>`` form. Lohner's canonical
        product pages are served at ``/products/<handle>``.
        """
        return re.sub(r"/collections/[^/]+/products/", "/products/", url)
