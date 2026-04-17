"""Archetype Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="archetype-coffee",
    display_name="Archetype Coffee",
    roaster_name="Archetype Coffee",
    website="https://drinkarchetype.com",
    description="Small batch coffee roaster based in Omaha, Nebraska, USA.",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="available",
)
class ArchetypeCoffeeScraper(ShopifyJsonScraper):
    """Scraper using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Archetype Coffee",
            base_url="https://drinkarchetype.com",
            products_json_urls=[
                "https://drinkarchetype.com/collections/archetype-coffee/products.json",
            ],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )
        # Exclude subscription products or other non-coffee items
        self.exclude_slugs = ["subscription", "drip-bag", "bundle", "cascara", "gift-card"]
