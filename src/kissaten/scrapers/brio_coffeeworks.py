"""Brio Coffeeworks scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="brio-coffeeworks",
    display_name="Brio Coffeeworks",
    roaster_name="Brio Coffeeworks",
    website="https://www.briocoffeeworks.com",
    description="Burlington, Vermont roaster sourcing and roasting Direct Trade relationships "
    "coffees with a focus on transparency and sustainability",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class BrioCoffeeworksScraper(ShopifyJsonScraper):
    """Scraper for Brio Coffeeworks (briocoffeeworks.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Brio Coffeeworks scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Brio Coffeeworks",
            base_url="https://www.briocoffeeworks.com",
            products_json_urls=["https://www.briocoffeeworks.com/collections/all-coffees/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Exclude non-bean products. The curated `all-coffees` collection keeps
        # the Fermentation Project Box Set and the Brio Tasting Gift Box in
        # (both are flagged as tasting kits downstream, not excluded).
        self.exclude_slugs = [
            "instant-coffee",
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

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Brio Coffeeworks product URLs.

        Brio's canonical product pages are the no-collection form
        ``/products/<handle>``, so strip the ``/collections/<slug>`` segment.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
