"""Cast Iron scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="cast-iron",
    display_name="Cast Iron",
    roaster_name="Cast Iron",
    website="https://castironroasters.com",
    description="UK-based specialty coffee roaster known for single-origin coffees and espresso blends",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class CastIronRoastersScraper(ShopifyJsonScraper):
    """Scraper for Cast Iron (castironroasters.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Cast Iron scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Cast Iron",
            base_url="https://castironroasters.com",
            products_json_urls=["https://castironroasters.com/products.json"],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude non-coffee products (subscriptions, gift cards, merchandise,
        # brewing equipment, and the Storm Tea / hot-chocolate range)
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
            # Cast Iron's actual non-coffee products:
            "cast-iron-fellow-carter-cup",
            "cast-iron-tee",
            "cast-iron-cap",
            "roasters-choice",
            "mork-hot-chocolate",
            "wilfa-filter-coffee-machine",
            "linea-mini",
            "paper-filters",
            "hario-immersion-dripper",
            "chemex-filter-papers",
            "coffee-maker-chemex",
            "reusable-coffee-cup-huskee",
            "green-tea-50-whole-leaf-silky-pyramids",
            "organic-caffeine-free-rooibos-indian-chai",
            "earl-grey-whole-leaf-50-tea-bags",
            "estate-breakfast-whole-leaf-tea-bags",
            "peppermint-tea",
            "english-breakfast",
            "earl-grey",
            "v60-coffee-decanter",
            "v60-coffee-dripper",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
