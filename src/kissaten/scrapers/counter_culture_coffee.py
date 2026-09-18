"""Counter Culture Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="counter-culture-coffee",
    display_name="Counter Culture",
    roaster_name="Counter Culture Coffee",
    website="https://counterculturecoffee.com",
    description="Durham, North Carolina-rooted specialty roaster offering year-round blends "
    "(Apollo, Big Trouble, Fast Forward), seasonal single origins, and coffee education; "
    "a pioneer of US direct-trade sourcing since 1995",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class CounterCultureCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Counter Culture Coffee (counterculturecoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Counter Culture Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Counter Culture Coffee",
            base_url="https://counterculturecoffee.com",
            products_json_urls=["https://counterculturecoffee.com/collections/coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The curated `coffee` collection still carries recurring
        # subscriptions (Blend Box, Single-Origin, Office Coffee, gift
        # subscriptions) — those are excluded. Multi-bag bundles (Bestseller,
        # Dark Roast, Decaf Lovers, ...) are genuine coffee and are kept.
        # Equipment (Baratza grinders), candles, apparel and gift cards are
        # filtered by the base class's name/handle categories.
        self.exclude_slugs = [
            "subscription",
        ]

        # Pin the home-market currency: this is a large store on Shopify
        # Markets with high geo-conversion risk. USD was verified against
        # /cart.json, so make it authoritative for datacenter-IP runs.
        self.store_currency = "USD"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Counter Culture product URLs.

        Canonical product pages are the no-collection form
        ``/products/<handle>``, so strip the ``/collections/<slug>`` segment.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
