"""Cult Coffee Roasters scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="cult-coffee-roasters",
    display_name="Cult Coffee Roasters",
    roaster_name="Cult Coffee Roasters",
    website="https://cultcoffeeroasters.com",
    description="Specialty coffee roaster based in Edinburgh, sourcing single origin coffees "
    "with a focus on experimental processing and unique flavour profiles",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class CultCoffeeRoastersScraper(ShopifyJsonScraper):
    """Scraper for Cult Coffee Roasters (cultcoffeeroasters.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Cult Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Cult Coffee Roasters",
            base_url="https://cultcoffeeroasters.com",
            products_json_urls=["https://cultcoffeeroasters.com/products.json"],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Exclude non-coffee products (apparel, accessories, gift cards, etc.)
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
            # Cult-specific: Inner Circle apparel/enamel pin line
            "inner-circle",
            "coffee-people",
            "long-sleeve",
            "short-sleeve",
            "enamel-pin",
            # Cult-specific: incense cones
            "incense",
            # Cult-specific: novelty £1M product
            "relic-of-revelation",
            "aergrind"
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
