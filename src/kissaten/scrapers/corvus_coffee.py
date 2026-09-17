"""Corvus Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="corvus-coffee",
    display_name="Corvus",
    roaster_name="Corvus",
    website="https://www.corvuscoffee.com",
    description="Denver, Colorado specialty roaster offering single origins, reserve lots and "
    "espresso-forward blends alongside direct-trade relationships in Colombia, Kenya and Ethiopia.",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class CorvusCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Corvus Coffee (corvuscoffee.com) using Shopify products.json.

    JSON-only extraction: the curated ``all-coffee`` collection contains only
    the bean lineup (single origins, reserve lots, blends and the decaf), and
    the ``body_html`` already carries process, variety, origin and flavor
    notes. Subscriptions live in the separate ``coffee`` collection, which we
    deliberately do not fetch.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Corvus Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Corvus",
            base_url="https://www.corvuscoffee.com",
            products_json_urls=[
                "https://www.corvuscoffee.com/collections/all-coffee/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Safety net only — the curated all-coffee collection is pure beans
        # (no subscriptions, wholesale, equipment or merch).
        self.exclude_slugs = [
            "subscription",
            "wholesale",
        ]

        # Pin the home-market currency (verified against /cart.js): Shopify
        # Markets may serve geo-converted prices to datacenter IPs.
        self.store_currency = "USD"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Corvus product URLs.

        Corvus' canonical product pages are the no-collection form
        ``/products/<handle>``, so strip the ``/collections/<slug>`` segment.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
