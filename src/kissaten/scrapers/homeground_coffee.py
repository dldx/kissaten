"""Homeground Coffee Roasters scraper implementation using Shopify JSON API."""

import logging
from typing import Any

from bs4 import BeautifulSoup

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="homeground",
    display_name="Homeground Coffee Roasters",
    roaster_name="Homeground Coffee Roasters",
    website="https://homegroundcoffeeroasters.com",
    description="Specialty coffee roaster based in Singapore.",
    requires_api_key=True,
    currency="SGD",
    country="Singapore",
    status="available",
)
class HomegroundCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Homeground Coffee Roasters using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Homeground Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Homeground Coffee Roasters",
            base_url="https://homegroundcoffeeroasters.com",
            products_json_urls=[
                "https://homegroundcoffeeroasters.com/collections/coffees-specialty/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str | None:
        """Standardize the product URL and filter out non-coffee products."""
        # Filter out subscriptions, bundles, and workshops if they appear
        excluded_patterns = ["subscription", "drip-bag", "bundle", "workshop", "gift-card", "accessories"]
        url_lower = url.lower()
        if any(pattern in url_lower for pattern in excluded_patterns):
            return None

        # Standardize to the canonical format (usually /products/<handle>)
        if "/products/" in url:
            handle = url.split("/products/")[-1]
            return f"{self.base_url}/products/{handle}"

        return url
