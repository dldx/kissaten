"""Album Coffee Roasters scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="album-coffee",
    display_name="Album Coffee Roasters",
    roaster_name="Album Coffee Roasters",
    website="https://albumcoffee.com",
    description=(
        "Specialty coffee roaster based in the UK, focusing on seasonal "
        "single origin coffees and unique flavor profiles."
    ),
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class AlbumCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Album Coffee Roasters (albumcoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Album Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Album Coffee Roasters",
            base_url="https://albumcoffee.com",
            products_json_urls=["https://albumcoffee.com/products.json"],
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
            "sampler",
            "taster-pack",
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
