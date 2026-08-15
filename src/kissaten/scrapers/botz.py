"""Botz Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="botz",
    display_name="Botz Coffee",
    roaster_name="Botz",
    website="https://botz-coffee.com",
    description="US-based specialty coffee micro-roaster known for playful, "
    "single-origin coffees and micro-lots sourced directly from producers.",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="available",
)
class BotzScraper(ShopifyJsonScraper):
    """Scraper for Botz Coffee (botz-coffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Botz Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Botz",
            base_url="https://botz-coffee.com",
            products_json_urls=["https://botz-coffee.com/collections/all/products.json"],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude non-coffee products (gift cards and merch) that Shopify lists
        # in the "all" collection alongside the coffee beans.
        self.exclude_slugs = [
            "gift-card",
            "t-shirt",
            "sweatshirt",
            "crew-neck",
            "subscription",
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
            "decal",
            "sticker",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Botz Coffee product URLs.

        The canonical product pages on botz-coffee.com are served at
        `/products/<handle>` (no collection segment). ShopifyJsonScraper builds
        URLs from the products.json base (`/collections/all/products/<handle>`),
        so strip the `collections/all` prefix to match the site's real URLs.
        """
        return url.replace("https://botz-coffee.com/collections/all", "https://botz-coffee.com")
