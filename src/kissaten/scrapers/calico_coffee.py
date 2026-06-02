"""Calico Coffee Roasters scraper."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="calico",
    display_name="Calico Coffee",
    roaster_name="Calico Coffee",
    website="https://calicocoffee.co.uk",
    description="Calico focuses on green bean sourcing and transparent supply chains, working with exceptional coffees from Panama, Kenya, Ethiopia, and Yunnan.",
    currency="GBP",
    country="United Kingdom",
    requires_api_key=True,
)
class CalicoScraper(ShopifyJsonScraper):
    """Scraper for Calico Coffee Roasters using Shopify JSON API."""

    def preprocess_product_url(self, url: str) -> str:
        """Ensure product URLs use the fixed /products/handle format, removing collections."""
        if "/products/" in url:
            handle = url.split("/products/")[-1]
            return f"{self.base_url}/products/{handle}"
        return url

    def __init__(self, api_key: str | None = None):
        """Initialize Calico Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Calico Coffee",
            base_url="https://calicocoffee.co.uk",
            products_json_urls=["https://calicocoffee.co.uk/collections/coffee/products.json"],
            scrape_product_pages=False,  # User explicitly asked not to scrape product pages
        )
        self.exclude_slugs = ["gift-card", "subscription", "merch", "equipment"]
