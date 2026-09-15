"""Driftaway Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="driftaway",
    display_name="Driftaway",
    roaster_name="Driftaway",
    website="https://store.driftaway.coffee",
    description="Brooklyn-based specialty coffee roaster known for its "
    "personalized taste-profile subscription and single origin coffee bags, "
    "including the James Hoffmann / Lucia Solis Fermentation Project kit.",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class DriftawayScraper(ShopifyJsonScraper):
    """Scraper for Driftaway (store.driftaway.coffee) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Driftaway scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Driftaway",
            base_url="https://store.driftaway.coffee",
            products_json_urls=["https://store.driftaway.coffee/collections/coffees/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The curated coffees collection holds coffee bags plus box sets
        # (including the Fermentation Project tasting kit, which is kept and
        # flagged downstream). Only the gift card needs excluding.
        self.exclude_slugs = [
            "gift-card",
            "gift",
            "subscription",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Driftaway product URLs.

        store.driftaway.coffee's canonical product pages are the
        no-collection form ``/products/<handle>``, so strip the
        ``/collections/<slug>`` segment.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
