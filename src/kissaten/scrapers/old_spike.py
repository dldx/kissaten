"""Old Spike Roastery scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="old-spike",
    display_name="Old Spike",
    roaster_name="Old Spike Roastery",
    website="https://oldspikeroastery.com",
    description="Old Spike Roastery: direct-trade, responsibly sourced speciality coffee. "
    "Every cup sold fuels the fight to reduce homelessness, 65% of profits "
    "support the mission.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class OldSpikeCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Old Spike Roastery (oldspikeroastery.com) using Shopify products.json.

    Old Spike publishes its beans across several overlapping collections
    (``coffee``, ``wholebean-coffees``, ``espresso``, ``filter-coffee``).
    Including them all means a product is discovered even if Old Spike
    reorganises a collection; ``preprocess_product_url`` canonicalises every
    collection URL to ``https://oldspikeroastery.com/products/<handle>`` (the
    exact form used on the live site and declared in its canonical link), so
    duplicate listings across collections collapse to one URL and are never
    scraped twice.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Old Spike Roastery scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Old Spike Roastery",
            base_url="https://oldspikeroastery.com",
            products_json_urls=[
                "https://oldspikeroastery.com/collections/old-spike-roastery-200g-coffee-bags/products.json",
            ],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Exclude non-coffee products. Every slug was verified against the
        # full current catalog: none is a substring of any real bean handle.
        # NOTE: the subscription "benedict-blend" (handle "benedict-blend")
        # CANNOT be excluded by slug — it is a substring of the real bean
        # handle "benedict-blend-espresso" — so it is dropped by the base
        # class name filter instead ("subscription" in its title).
        self.exclude_slugs = [
            "4kgs",  # bulk 4kg quantity SKU, not a specific coffee
            "coffee-explorer-bundle",  # multi-coffee Christmas bundle
            "reusable-coffee-tin",  # branded reusable tin
            "roasters-choice",  # rotating "Roaster's Choice" subscription
            # Defensive common non-coffee slugs (all verified safe: no bean
            # handle contains any of them).
            "gift-card",
            "giftcard",
            "subscription",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "merch",
            "tumbler",
            "hoodie",
            "tshirt",
            "capsules",
            "taster-pack",
            "sampler",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
