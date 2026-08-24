"""Established Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="established",
    display_name="Established Coffee",
    roaster_name="Established",
    website="https://established.coffee",
    description="London-based specialty coffee roaster (ESTD. / Established Coffee), "
    "known for conscientious sourcing, transparent trade and reliably excellent coffee.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class EstablishedCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Established Coffee (established.coffee) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Established Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Established",
            base_url="https://established.coffee",
            products_json_urls=[
                "https://established.coffee/collections/coffee/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Pin GBP: the store is UK-marketed and products.json serves no
        # currency marker, so the geo-detected value must not override.
        self.store_currency = "GBP"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Established Coffee product URLs to the canonical form.

        The products.json collection base yields
        ``/collections/coffee/products/<handle>``, but the site's canonical
        product pages are ``/products/<handle>`` (the ``rel=canonical`` link
        points there), so the collection segment is stripped.
        """
        if "/products/" in url:
            handle = url.split("/products/", 1)[-1]
            return f"{self.base_url}/products/{handle}"
        return url
