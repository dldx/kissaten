"""Calendar Coffee scraper implementation using Shopify JSON API."""

import logging

from ..ai import CoffeeDataExtractor
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="calendar-coffee",
    display_name="Calendar Coffee",
    roaster_name="Calendar Coffee",
    website="https://calendarcoffee.ie",
    description="Roastery founded to champion seasonal coffee, based in Ireland.",
    requires_api_key=True,
    currency="EUR",
    country="Republic of Ireland",
    status="available",
)
class CalendarCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Calendar Coffee (calendarcoffee.ie) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Calendar Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Calendar Coffee",
            base_url="https://calendarcoffee.ie",
            products_json_urls=[
                "https://calendarcoffee.ie/collections/fresh-harvests/products.json",
            ],
            scrape_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str | None:
        """Standardize the product URL and filter out non-coffee products."""
        # Filter out non-coffee products (merch, equipment, etc.)
        excluded_patterns = ["test-roast", "wilfa"]
        url_lower = url.lower()
        if any(pattern in url_lower for pattern in excluded_patterns):
            return None

        # Standardize to the format provided in the example
        if "/products/" in url:
            handle = url.split("/products/")[-1]
            return f"{self.base_url}/collections/fresh-harvests/products/{handle}"

        return url
