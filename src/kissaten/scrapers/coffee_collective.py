"""Coffee Collective scraper implementation with AI-powered extraction."""

import logging
from typing import Any

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="coffee-collective",
    display_name="Coffee Collective",
    roaster_name="Coffee Collective",
    website="https://coffeecollective.dk",
    description="Danish specialty coffee roaster based in Copenhagen, focusing on direct trade relationships with farmers.",
    requires_api_key=True,
    currency="DKK",
    country="Denmark",
    status="available",
)
class CoffeeCollectiveScraper(ShopifyJsonScraper):
    """Scraper for Coffee Collective (coffeecollective.dk) with AI-powered extraction."""

    def preprocess_product_url(self, url: str) -> str:
        """Ensure product URLs use the fixed /products/handle format, removing collections."""
        if "/products/" in url:
            handle = url.split("/products/")[-1]
            return f"{self.base_url}/products/{handle}"
        return url

    def __init__(self, api_key: str | None = None):
        """Initialize Coffee Collective scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Coffee Collective",
            base_url="https://coffeecollective.dk",
            products_json_urls=[
                "https://coffeecollective.dk/collections/filter-coffee/products.json",
                "https://coffeecollective.dk/collections/espresso/products.json",
            ],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

        # Exclude common non-coffee products
        self.exclude_slugs = [
            "taster-pack",
            "advent-calendar",
            "gift-card",
            "subscription",
            "workshop",
            "equipment",
            "merchandise",
        ]

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup | Tag:
        """Isolate the specific section for more efficient extraction."""
        if section := soup.select_one("div.about-this-section"):
            return section
        return soup
