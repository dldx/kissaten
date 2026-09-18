"""Nucleus Coffee scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="nucleus-coffee",
    display_name="Nucleus Coffee",
    roaster_name="Nucleus Coffee",
    website="https://nucleuscoffee.com",
    description="Canadian specialty coffee roaster in Montreal roasting experimental "
    "single origins, home of the Kit du Projet Fermentation de James Hoffmann.",
    requires_api_key=True,
    currency="CAD",
    country="Canada",
    status="experimental",
)
class NucleusCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Nucleus Coffee (nucleuscoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Nucleus Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Nucleus Coffee",
            base_url="https://nucleuscoffee.com",
            products_json_urls=["https://nucleuscoffee.com/collections/all/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=1.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # collections/all mixes coffee with subscriptions, cupping gear and
        # xbloom machines (the taste-based collections overlap, so /all plus
        # excludes is the cleanest listing).
        self.exclude_slugs = [
            "subscription",
            "club-lab",
            "cupping-bowls",
            "cupping-spoon",
            "xbloom",
            "gift-card",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Strip the collection segment to match Nucleus' canonical product URLs.

        ShopifyJsonScraper builds product URLs as
        ``<products.json base>/products/<handle>``, which yields a
        ``/collections/all/products/<handle>`` form. Nucleus' canonical
        product pages are served at ``/products/<handle>``.
        """
        return re.sub(r"/collections/[^/]+/products/", "/products/", url)
