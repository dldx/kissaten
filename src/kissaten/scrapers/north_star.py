"""North Star Coffee Roasters scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="north-star",
    display_name="North Star Coffee Roasters",
    roaster_name="North Star Coffee Roasters",
    website="https://www.northstarroast.com",
    description="B Corp certified specialty coffee roastery in Leeds, driven by "
    "impact over profit — people and planet come first in every "
    "decision they make.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class NorthStarCoffeeScraper(ShopifyJsonScraper):
    """Scraper for North Star Coffee Roasters (northstarroast.com) using Shopify products.json.

    North Star publishes its coffee across three overlapping collections
    (``coffee``, ``all-coffee``, ``base-coffee``). Including all of them means
    a product is discovered even if North Star reorganises one collection;
    ``preprocess_product_url`` canonicalises every collection URL to
    ``https://www.northstarroast.com/products/<handle>`` (the exact form used
    on the live site), so duplicate listings across collections collapse to
    one URL and are never scraped twice.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize North Star Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="North Star Coffee Roasters",
            base_url="https://www.northstarroast.com",
            products_json_urls=[
                "https://www.northstarroast.com/collections/coffee/products.json",
            ],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Exclude non-coffee products. "bundle", "variety-pack" and
        # "subscription" are distinctive substrings that match every
        # multi-bag/gift/subscription handle but NO coffee-bean handle
        # (verified against the full 29-handle catalog: bundles such as
        # "astro-the-docks-bundle" and packs such as "base-range-variety-pack"
        # are caught, while beans like "burundi-ryamukona-washed" pass).
        self.exclude_slugs = [
            "subscription",
            "bundle",
            "variety-pack",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
