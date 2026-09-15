"""PS Coffee Roasters scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="ps-coffee-roasters",
    display_name="PS Coffee Roasters",
    roaster_name="PS Coffee Roasters",
    website="https://pscoffeeroasters.com",
    description="Amsterdam-based specialty coffee roaster roasting single origins "
    "for filter and espresso, home of the James Hoffmann Fermentation Project collaboration.",
    requires_api_key=True,
    currency="EUR",
    country="Netherlands",
    status="experimental",
)
class PSCoffeeRoastersScraper(ShopifyJsonScraper):
    """Scraper for PS Coffee Roasters (pscoffeeroasters.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize PS Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="PS Coffee Roasters",
            base_url="https://pscoffeeroasters.com",
            products_json_urls=["https://pscoffeeroasters.com/collections/coffee-1/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=1.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The curated "Coffee" collection still lists two internal test
        # products and two subscription clubs.
        self.exclude_slugs = [
            "test-roast",
            "test-subscriptions",
            "subscription",
            "club",
            "gift-card",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Strip the collection segment to match PS Coffee's canonical product URLs.

        ShopifyJsonScraper builds product URLs as
        ``<products.json base>/products/<handle>``, which yields a
        ``/collections/coffee-1/products/<handle>`` form. PS Coffee's canonical
        product pages are served at ``/products/<handle>``.
        """
        return re.sub(r"/collections/[^/]+/products/", "/products/", url)
