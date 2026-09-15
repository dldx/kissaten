"""Farmhand Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="farmhand-coffee",
    display_name="Farmhand Coffee",
    roaster_name="Farmhand Coffee",
    website="https://www.farmhandcoffee.ie",
    description="Kilkenny-based Irish specialty roaster offering single-origin filter and "
    "espresso coffees sourced directly from producers",
    requires_api_key=True,
    currency="EUR",
    country="Republic of Ireland",
    status="experimental",
)
class FarmhandCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Farmhand Coffee (farmhandcoffee.ie) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Farmhand Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Farmhand Coffee",
            base_url="https://www.farmhandcoffee.ie",
            products_json_urls=[
                "https://www.farmhandcoffee.ie/collections/filter-coffee-beans/products.json",
                "https://www.farmhandcoffee.ie/collections/esspresso-coffee-beans-ground/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The two curated collections (filter / espresso beans) keep the
        # Fermentation Project kit; only the cold brew bags are not beans.
        self.exclude_slugs = [
            "cold-brew-bags",
        ]

        # Pin the home-market currency: Shopify Markets may serve
        # geo-converted prices to datacenter IPs, and the base-class
        # display-name currency lookup falls back to GBP. The home
        # currency was verified against /cart.js, so make it authoritative.
        self.store_currency = "EUR"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Farmhand Coffee product URLs.

        Farmhand's canonical product pages are the no-collection form
        ``/products/<handle>``; stripping the collection segment also dedups
        products that appear in both the filter and espresso collections.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
