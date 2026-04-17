"""Rish Coffee Roasters scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="rish",
    display_name="Rish Coffee Roasters",
    roaster_name="Rish Coffee Roasters",
    website="https://rishcoffee.com",
    description="UK-based specialty coffee roaster focusing on fresh roast-to-order single origins and blends.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class RishCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Rish Coffee Roasters (rishcoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Rish Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Rish Coffee Roasters",
            base_url="https://rishcoffee.com",
            products_json_urls=[
                "https://rishcoffee.com/collections/all/products.json",
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
            "vial",
            "bundle",
            "single-dose-coffee-vial",
        ]
