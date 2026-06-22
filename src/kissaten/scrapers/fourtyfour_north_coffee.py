"""44 North Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="44-north-coffee",
    display_name="44 North Coffee",
    roaster_name="44 North Coffee",
    website="https://44northcoffee.com",
    description="Women-owned small batch coffee roaster focused on fair trade organic beans, based in Deer Isle, Maine, USA.",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="available",
)
class FourtyFourNorthCoffeeScraper(ShopifyJsonScraper):
    """Scraper for 44 North Coffee (44northcoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize 44 North Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="44 North Coffee",
            base_url="https://44northcoffee.com",
            products_json_urls=[
                "https://44northcoffee.com/collections/fair-trade-organic-beans/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )
        # Exclude subscription products or other non-coffee items
        self.exclude_slugs = [
            "subscription",
            "drip-bag",
            "bundle",
            "canned",
            "sampler",
            "cascara",
            "chai-tea",
            "teapot",
            "matcha",
            "granola",
            "cocoa",
            "chocolate",
            "dripper",
            "tritan",
            "latte-mix"
        ]
