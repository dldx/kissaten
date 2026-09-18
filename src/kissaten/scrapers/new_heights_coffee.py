"""New Heights Coffee Roasters scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="new-heights-coffee",
    display_name="New Heights Coffee Roasters",
    roaster_name="New Heights Coffee Roasters",
    website="https://newheightscoffee.com",
    description="US specialty coffee roaster roasting single origins and espresso "
    "blends, home of the Fermentation Project set (James Hoffmann collaboration).",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class NewHeightsCoffeeScraper(ShopifyJsonScraper):
    """Scraper for New Heights Coffee Roasters (newheightscoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize New Heights Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="New Heights Coffee Roasters",
            base_url="https://newheightscoffee.com",
            products_json_urls=["https://newheightscoffee.com/collections/coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=1.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The curated Coffee collection only contains bean products; keep a
        # defensive exclude list for merch/equipment leaks.
        self.exclude_slugs = [
            "gift-card",
            "hat",
            "merch",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Strip the collection segment to match New Heights' canonical product URLs.

        ShopifyJsonScraper builds product URLs as
        ``<products.json base>/products/<handle>``, which yields a
        ``/collections/coffee/products/<handle>`` form. New Heights' canonical
        product pages are served at ``/products/<handle>``.
        """
        return re.sub(r"/collections/[^/]+/products/", "/products/", url)
