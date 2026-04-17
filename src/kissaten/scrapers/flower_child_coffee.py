"""Flower Child Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="flower-child-coffee",
    display_name="Flower Child Coffee",
    roaster_name="Flower Child Coffee",
    website="https://flowerchildcoffee.com",
    description="Coffee roaster based in Oakland, California focused on clean, vibrant cups.",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="available",
)
class FlowerChildCoffeeScraper(ShopifyJsonScraper):
    """Scraper using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Flower Child Coffee",
            base_url="https://flowerchildcoffee.com",
            products_json_urls=[
                "https://flowerchildcoffee.com/collections/active-coffee/products.json",
                "https://flowerchildcoffee.com/collections/archive/products.json",
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
