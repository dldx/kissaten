"""Zero to One Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="zero-to-one",
    display_name="Zero to One",
    roaster_name="Zero to One",
    website="https://zerotoonecoffee.co.uk",
    description=(
        "Specialty coffee roaster based in London, UK, specializing in fine "
        "Vietnamese robusta and specialty arabica coffees."
    ),
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class ZeroToOneScraper(ShopifyJsonScraper):
    """Scraper for Zero to One Coffee (zerotoonecoffee.co.uk) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Zero to One Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Zero to One",
            base_url="https://zerotoonecoffee.co.uk",
            products_json_urls=["https://zerotoonecoffee.co.uk/products.json"],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Exclude non-coffee products (subscriptions, gift cards, equipment, etc.)
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "-pack-",
            "apparel",
            "mug",
            "tumbler",
            "hoodie",
            "tshirt",
            "capsules",
            "pods",
            "cold-brew-cans",
            "easy-pour",
            "filter",
            "phin",
            "kit",
            "set",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
