"""Method Coffee Roasters scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="method-coffee",
    display_name="Method Coffee Roasters",
    roaster_name="Method Coffee Roasters",
    website="https://methodroastery.com",
    description="UK specialty coffee roaster in Brighton roasting seasonal single "
    "origins and blends for filter and espresso.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="experimental",
)
class MethodCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Method Coffee Roasters (methodroastery.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Method Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Method Coffee Roasters",
            base_url="https://methodroastery.com",
            products_json_urls=["https://methodroastery.com/collections/coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=1.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The curated COFFEE collection only contains bean products; keep a
        # defensive exclude list for future equipment/subscription leaks.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "equipment",
            "brewing",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Strip the collection segment to match Method's canonical product URLs.

        ShopifyJsonScraper builds product URLs as
        ``<products.json base>/products/<handle>``, which yields a
        ``/collections/coffee/products/<handle>`` form. Method's canonical
        product pages are served at ``/products/<handle>``.
        """
        return re.sub(r"/collections/[^/]+/products/", "/products/", url)
