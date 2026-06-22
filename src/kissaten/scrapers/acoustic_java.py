"""Acoustic Java Coffee Roaster scraper implementation with Shopify JSON extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="acoustic-java",
    display_name="Acoustic Java",
    roaster_name="Acoustic Java",
    website="https://acousticjava.com",
    description="Specialty coffee roaster based in Worcester, MA",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="available",
)
class AcousticJavaScraper(ShopifyJsonScraper):
    """Scraper for Acoustic Java (acousticjava.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Acoustic Java scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Acoustic Java",
            base_url="https://acousticjava.com",
            products_json_urls=[
                "https://acousticjava.com/collections/light-roast/products.json",
                "https://acousticjava.com/collections/medium-roast/products.json",
                "https://acousticjava.com/collections/dark-roast/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude non-coffee products (subscriptions, equipment, etc.)
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "accessory",
            "merchandise",
            "3-bags-of-coffee",
            "test-roast",
            "t-shirt",
            "sweatshirt",
            "matcha",
            "tumbler",
            "collection-box",
            "voyager", # bean origin not specific enough
            "grouchys", # bean origin not specific enough
            "roastmeister" # bean origin not specific enough
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
