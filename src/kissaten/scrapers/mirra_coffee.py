"""Mirra Coffee scraper implementation using ShopifyJsonScraper."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="mirra-coffee",
    display_name="Mirra Coffee",
    roaster_name="Mirra Coffee",
    website="https://www.mirracoffee.com",
    description="The American Nordic Roastery specializing in hyper-local, "
    "single-producer lots with Nordic-style light roasting",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="available",
)
class MirraCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Mirra Coffee (mirracoffee.com) using Shopify's products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Mirra Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Mirra Coffee",
            base_url="https://www.mirracoffee.com",
            products_json_urls=["https://www.mirracoffee.com/products.json"],
            use_optimized_mode=True,
            scrape_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )
        self.exclude_slugs = ["subscription", "gift-card", "wholesale"]
