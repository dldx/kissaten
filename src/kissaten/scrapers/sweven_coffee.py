"""Sweven Coffee scraper implementation with AI-powered extraction."""

import logging

from bs4 import BeautifulSoup, Tag

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="sweven",
    display_name="Sweven Coffee",
    roaster_name="Sweven Coffee",
    website="https://www.swevencoffee.co.uk",
    description="UK-based specialty coffee roaster focusing on rare, exclusive, and microlot coffees",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class SwevenCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Sweven Coffee using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Sweven Coffee scraper.

        Args:
            api_key: Optional API key for AI-powered extraction.
        """
        super().__init__(
            roaster_name="Sweven Coffee",
            base_url="https://www.swevencoffee.co.uk",
            products_json_urls=[
                "https://swevencoffee.co.uk/products.json",
            ],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        # Exclude non-coffee products
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "accessory",
            "merchandise",
            "test-roast",
            "magazine",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup | Tag:
        """Extract only the main content section for AI extraction."""
        # Focus on the section containing the product details
        content = soup.select_one("div.section-content")
        if content:
            logger.debug("Limiting AI extraction to main product content section.")
            return content

        return soup
