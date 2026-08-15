"""20grams Coffee Roastery scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="twenty-grams",
    display_name="20grams Coffee Roastery",
    roaster_name="20grams Coffee Roastery",
    website="https://20gramscoffeeroastery.com",
    description="Singapore-based specialty coffee roaster, known for carefully sourced "
    "single origins and blends roasted with precision.",
    requires_api_key=True,
    currency="SGD",
    country="Singapore",
    status="available",
)
class TwentyGramsCoffeeScraper(ShopifyJsonScraper):
    """Scraper for 20grams Coffee Roastery (20gramscoffeeroastery.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize 20grams Coffee Roastery scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="20grams Coffee Roastery",
            base_url="https://20gramscoffeeroastery.com",
            products_json_urls=["https://20gramscoffeeroastery.com/products.json"],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude non-coffee products (masterclasses, water kits, brewing
        # equipment, apparel, BWT filters, and internal test roasts). Note that
        # this store mislabels many non-coffee items as "Coffee Beans - Roasted",
        # so slug-based exclusion is the reliable filter.
        self.exclude_slugs = [
            "water-kit",
            "masterclass",
            "brewing",
            "puck-screen",
            "bwt",
            "washed-coffee",
            "varietal",
            "roasting",
            "test-roast",
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "accessory",
            "merchandise",
            "t-shirt",
            "apparel",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
