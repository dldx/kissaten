"""Onoma Kaffee scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="onoma-kaffee",
    display_name="Onoma Kaffee",
    roaster_name="Onoma Kaffee",
    website="https://onoma.coffee",
    description="Helsinki-born, Flensburg-based Greek-German specialty coffee roastery "
    "roasting seasonal single origins, home of the Fermentation Project set.",
    requires_api_key=True,
    currency="EUR",
    country="Germany",
    status="experimental",
)
class OnomaKaffeeScraper(ShopifyJsonScraper):
    """Scraper for Onoma Kaffee (onoma.coffee) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Onoma Kaffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Onoma Kaffee",
            base_url="https://onoma.coffee",
            products_json_urls=["https://onoma.coffee/collections/kaffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=1.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The curated "Kaffee" collection only contains bean products; keep a
        # defensive exclude list for equipment/course leaks.
        self.exclude_slugs = [
            "gift-card",
            "gutschein",
            "kurs",
            "aeropress",
            "filterpapier",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Strip the collection segment to match Onoma's canonical product URLs.

        ShopifyJsonScraper builds product URLs as
        ``<products.json base>/products/<handle>``, which yields a
        ``/collections/kaffee/products/<handle>`` form. Onoma's canonical
        product pages are served at ``/products/<handle>``.
        """
        return re.sub(r"/collections/[^/]+/products/", "/products/", url)
