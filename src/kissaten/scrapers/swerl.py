"""Swerl Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="swerl",
    display_name="Swerl",
    roaster_name="Swerl",
    website="https://swerl.se",
    description="Coffee roaster based in Falkenberg, Sweden focused on vibrant and seasonal coffees.",
    requires_api_key=True,
    currency="SEK",
    country="Sweden",
    status="available",
)
class SwerlCoffeeScraper(ShopifyJsonScraper):
    """Scraper using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Swerl",
            base_url="https://swerl.se",
            products_json_urls=[
                "https://swerl.se/collections/filter-coffee/products.json",
                "https://swerl.se/collections/espresso/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )
        # Exclude subscription products or other non-coffee items
        self.exclude_slugs = ["subscription", "drip-bag", "mystery-coffee", "bundle", "pods", "cascara", "gift-card"]
