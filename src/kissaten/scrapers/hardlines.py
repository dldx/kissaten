"""Hardlines scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="hardlines",
    display_name="Hardlines",
    roaster_name="Hardlines",
    website="https://hard-lines.co.uk",
    description="London-based specialty coffee roaster and cafe from the team behind "
    "Canton, known for accessible, well-rounded blends and single origins.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class HardlinesScraper(ShopifyJsonScraper):
    """Scraper for Hardlines (hard-lines.co.uk) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Hardlines scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Hardlines",
            base_url="https://hard-lines.co.uk",
            products_json_urls=["https://hard-lines.co.uk/collections/all/products.json"],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude non-coffee products. The `all` collection is heavily mixed with
        # equipment, apparel, merch, courses, subscriptions, pods and liqueur.
        # Substring-matched against the Shopify handle, keeping the actual bean
        # products (the-canton-blend, for-the-forest, i-heart-decaf, honduras-*,
        # nicaragua-*, uganda-maliba, coffee-house-party-brazilian-beans, brew-pack).
        self.exclude_slugs = [
            # Generic non-coffee categories
            "subscription",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "sampler",
            "apparel",
            "mug",
            "hoodie",
            "tshirt",
            "capsules",
            "pods",
            # Brewing equipment
            "aeropress",
            "hario",
            "fellow-opus",
            "grinder",
            "dripper",
            "orea",
            "timemore",
            # Apparel
            "t-shirt",
            "core-t",
            "run-club-t",
            "birthday-t",
            "ten-year-t",
            "breakfast",
            # Mugs / cups / pins / keyrings / glass / stickers
            "classic-cap",
            "classic-cup",
            "enamel",
            "diner-mug",
            "hardlinesglass",
            "sticker-pack",
            # Courses and vouchers
            "course",
            "workshop",
            "voucher",
            # Liqueur
            "liqueur",
            # Book
            "growing-a-coffee-business",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
