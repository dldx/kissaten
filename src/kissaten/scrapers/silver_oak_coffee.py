"""Silver Oak Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="silver-oak-coffee",
    display_name="Silver Oak Coffee",
    roaster_name="Silver Oak Coffee",
    website="https://silveroakcoffee.co.uk",
    description="Specialty coffee roaster based in Cambridgeshire, sourcing single origin coffees from Latin America, Africa, and beyond",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class SilverOakCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Silver Oak Coffee (silveroakcoffee.co.uk) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Silver Oak Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Silver Oak Coffee",
            base_url="https://silveroakcoffee.co.uk",
            products_json_urls=["https://silveroakcoffee.co.uk/collections/shop-all-coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "sampler",
            "taster-pack",
            "apparel",
            "mug",
            "tumbler",
            "hoodie",
            "tshirt",
            "capsules",
            "pods",
            "cold-brew-cans",
            "easy-pour",
            "selection-pack",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)