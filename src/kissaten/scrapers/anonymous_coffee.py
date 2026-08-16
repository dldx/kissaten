"""Anonymous Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="anonymous",
    display_name="Anonymous",
    roaster_name="Anonymous",
    website="https://anonymouscoffee.co.uk",
    description="London-based independent speciality coffee roaster sourcing fresh "
    "single-origin and blended coffees, roasted in small batches.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class AnonymousCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Anonymous Coffee (anonymouscoffee.co.uk) using Shopify products.json.

    The store is a plain Shopify shop with a single root ``products.json``
    endpoint that already carries the full bean info, so we scrape the
    JSON only (product pages are not fetched).
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Anonymous Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Anonymous",
            base_url="https://anonymouscoffee.co.uk",
            products_json_urls=["https://anonymouscoffee.co.uk/products.json"],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude non-coffee products: the catalogue mixes beans with
        # apparel (trucker cap, logo tee) and brewing equipment (Chemex
        # filter papers, AeroPress, Hario V60 brewers and filter papers).
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
            "trucker-cap",
            "logo-tee",
            "chemex",
            "filter-papers",
            "aeropress",
            "hario",
            "brewer",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
