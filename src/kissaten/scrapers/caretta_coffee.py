"""Caretta Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="caretta-coffee",
    display_name="Caretta Coffee",
    roaster_name="Caretta Coffee",
    website="https://carettacoffee.com",
    description=(
        "Specialty coffee roaster based in the UK, offering high quality "
        "single origin and micro-lot coffees."
    ),
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class CarettaCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Caretta Coffee (carettacoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Caretta Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Caretta Coffee",
            base_url="https://carettacoffee.com",
            products_json_urls=["https://carettacoffee.com/products.json"],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Exclude non-coffee products (subscriptions, tickets, equipment, apparel, accessories)
        self.exclude_slugs = [
            "subscription",
            "ticket",
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
            "hoodie",
            "t-shirt",
            "tee",
            "cap",
            "mug",
            "spoon",
            "grinder",
            "pitcher",
            "tamper",
            "server",
            "dripper",
            "scale",
            "kettle",
            "autocomb",
            "pump",
            "brewer",
            "maker",
            "acaia",
            "trey",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
