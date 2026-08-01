"""Elsewhere Coffee scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="elsewhere-coffee",
    display_name="Elsewhere Coffee",
    roaster_name="Elsewhere Coffee",
    website="https://elsewherecoffee.com",
    description="Specialty coffee roaster based in the UK",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class ElsewhereCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Elsewhere Coffee using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Elsewhere Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Elsewhere Coffee",
            base_url="https://elsewherecoffee.com",
            products_json_urls=[
                "https://elsewherecoffee.com/collections/frontpage/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude non-coffee products (courses, equipment, machines, apparel, etc.)
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "voucher",
            "course",
            "workshop",
            "machine",
            "grinder",
            "kettle",
            "brewer",
            "dripper",
            "scale",
            "filter",
            "tee",
            "cap",
            "bag",
            "merch",
            "apparel",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Normalize product URLs to ``/products/<handle>`` by stripping collection segments."""
        return re.sub(r"^(https?://[^/]+)/collections/[^/]+/", r"\1/", url)
