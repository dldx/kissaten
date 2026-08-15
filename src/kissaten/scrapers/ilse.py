"""Ilse Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="ilse",
    display_name="Ilse",
    roaster_name="Ilse",
    website="https://ilsecoffee.com",
    description="US specialty coffee roaster (ilsecoffee.com) offering a curated, seasonally "
    "rotating selection of single-origin coffees sourced directly from producers.",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="available",
)
class IlseCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Ilse Coffee (ilsecoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Ilse Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Ilse",
            base_url="https://ilsecoffee.com",
            products_json_urls=["https://ilsecoffee.com/collections/all-products/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Exclude non-coffee products (subscriptions, gift cards, merchandise, etc.)
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "t-shirt",
            "shirt",
            "merch",
            "equipment",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Strip the collection segment so product URLs are the canonical form.

        The products.json URL is under ``/collections/all-products``, which makes the base
        class build ``/collections/all-products/products/<handle>`` URLs. Ilse's canonical
        product pages are just ``/products/<handle>``, so we strip the collection segment.
        """
        return url.replace("/collections/all-products/products/", "/products/")
