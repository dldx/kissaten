"""Obra Coffee Roasters scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="obra-coffee",
    display_name="Obra Coffee Roasters",
    roaster_name="Obra Coffee Roasters",
    website="https://obracoffee.com",
    description="Small-batch specialty coffee roaster based in East Sussex, UK. "
    "Founded by Patrick and named after the Spanish word for 'work', a nod to his "
    "Cuban-American heritage, with single origin coffees roasted weekly.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class ObraCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Obra Coffee Roasters (obracoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Obra Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Obra Coffee Roasters",
            base_url="https://obracoffee.com",
            products_json_urls=[
                "https://obracoffee.com/collections/espresso/products.json",
                "https://obracoffee.com/collections/filter/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
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
            "apparel",
            "mug",
            "tumbler",
            "hoodie",
            "tshirt",
            "capsules",
            "pods",
            "cold-brew-cans",
            "easy-pour",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Strip the collection segment so URLs use the canonical /products/ form.

        Shopify products.json URLs include the collection path (e.g.
        https://obracoffee.com/collections/espresso/products/la-bolsa-guatemala),
        but Obra's canonical product URLs are root-level
        (https://obracoffee.com/products/la-bolsa-guatemala).
        """
        return re.sub(r"/collections/[^/]+(?=/products/)", "", url)
