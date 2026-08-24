"""Frazers Coffee Roasters scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="frazers",
    display_name="Frazers Coffee Roasters",
    roaster_name="Frazers",
    website="https://www.frazerscoffeeroasters.co.uk",
    description="Sheffield-based specialty coffee roaster (since 2014) known for the "
    "Full Monty Espresso blend, Steel City Blend, and single origin coffees from "
    "Colombia, Brazil, Peru and Uganda, including an organic C02-process decaf.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class FrazersScraper(ShopifyJsonScraper):
    """Scraper for Frazers Coffee Roasters (frazerscoffeeroasters.co.uk) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Frazers Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Frazers",
            base_url="https://www.frazerscoffeeroasters.co.uk",
            products_json_urls=[
                "https://www.frazerscoffeeroasters.co.uk/collections/coffee/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=1.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Frazers is a Sheffield roaster priced in GBP (its home market; the
        # collection and products.json serve GBP at rate 1.0 with no
        # market-converted presentment for other geographies). Pin the currency
        # so the AI never prices a bean in a geo-detected currency.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Exclude genuine non-bean products that leak into the coffee
        # collection (a mug, a gift card, a gift note add-on, and jute sacks).
        # Sampler/taster boxes (Blend's Box, Origin Box, Mega Box) and the
        # coffee Gift Set are kept and scraped as coffee.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "giftcard",
            "gift-note",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "merch",
            "mug",
            "jute",
            "sacks",
            "apparel",
            "clothing",
            "capsules",
            "pods",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Strip the collection segment to match Frazers' canonical product URLs.

        ShopifyJsonScraper builds product URLs from the products.json base, which
        yields a ``/collections/coffee/products/<handle>`` form. Frazers' real
        (canonical) product pages are served at ``/products/<handle>`` on the
        ``www.`` host, so normalize the URL to that form.
        """
        return re.sub(r"/collections/[^/]+/products/", "/products/", url)
