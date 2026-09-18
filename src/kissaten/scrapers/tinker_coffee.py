"""Tinker Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="tinker-coffee",
    display_name="Tinker Coffee",
    roaster_name="Tinker Coffee",
    website="https://www.tinkercoffee.com",
    description="Indianapolis, Indiana specialty roaster offering approachable and adventurous "
    "single origins and blends",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class TinkerCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Tinker Coffee (tinkercoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Tinker Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Tinker Coffee",
            base_url="https://www.tinkercoffee.com",
            products_json_urls=["https://www.tinkercoffee.com/collections/coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The curated `coffee` collection keeps the sample packs (flagged as
        # tasting kits downstream); only the subscriptions are excluded.
        self.exclude_slugs = [
            "subscription",
        ]

        # Pin the home-market currency: Shopify Markets may serve
        # geo-converted prices to datacenter IPs, and the base-class
        # display-name currency lookup falls back to GBP. The home
        # currency was verified against /cart.js, so make it authoritative.
        self.store_currency = "USD"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def is_coffee_product_url(self, url: str, required_path_patterns: list[str] | None = None) -> bool:
        """Keep Tinker's 'adventurous' coffees despite the base-class filter.

        The base URL filter excludes the ``advent`` pattern (advent
        calendars), which also matches Tinker's 'adventurous' product line
        (e.g. ``adventurous-sample-pack``). Whitelist that prefix and defer to
        the base filter for everything else.
        """
        if "/products/adventurous" in url:
            return True
        return super().is_coffee_product_url(url, required_path_patterns)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Tinker Coffee product URLs.

        Tinker's canonical product pages are the no-collection form
        ``/products/<handle>``, so strip the ``/collections/<slug>`` segment.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
