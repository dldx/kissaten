"""cafēn scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="cafen",
    display_name="cafēn",
    roaster_name="cafēn",
    website="https://cafen.co.uk",
    description="Edinburgh-based modern roasting company offering intentionally light-roasted coffees with a focus on connection, craft, and community.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class CafenScraper(ShopifyJsonScraper):
    """Scraper for cafēn using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize cafēn scraper.

        Args:
            api_key: Optional API key for AI-powered extraction.
        """
        super().__init__(
            roaster_name="cafēn",
            base_url="https://cafen.co.uk",
            products_json_urls=[
                "https://cafen.co.uk/products.json",
            ],
            rate_limit_delay=1.5,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
            scrape_product_pages=True,
        )

        # Exclude non-coffee products
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "merchandise",
            "equipment",
            "accessory",
            "delivery",
            "shipping",
            "postcard",
            "keep-cup"
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
