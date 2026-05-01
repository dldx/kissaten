"""Blue Tokai Coffee scraper implementation using Shopify JSON API."""

import logging
from typing import Any

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="blue-tokai",
    display_name="Blue Tokai Coffee",
    roaster_name="Blue Tokai Coffee Roasters",
    website="https://bluetokaicoffee.com",
    description="Delhi-based specialty coffee roaster known for fresh single-origin and blends",
    requires_api_key=True,
    currency="INR",
    country="India",
    status="available",
)
class BlueTokaiCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Blue Tokai Coffee (bluetokaicoffee.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Blue Tokai Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Blue Tokai Coffee Roasters",
            base_url="https://bluetokaicoffee.com",
            products_json_urls=[
                "https://bluetokaicoffee.com/collections/roasted-and-ground-coffee-beans/products.json",
            ],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str | None:
        """Standardize the product URL and filter out non-coffee products."""
        excluded_patterns = [
            "5-in-1-explorer-pack",
            "the-rich-bold-trio-pack",
            "subscription",
            "equipment",
            "brewing-equipment",
            "merchandise",
            "merch",
            "accessories",
            "filter",
            "dripper",
            "carafe",
            "grinder",
            "kettle",
            "scale",
            "gift-card",
            "gift-voucher",
            "tshirt",
            "hoodie",
            "apparel",
            "capsules",
            "pods",
            "easy-pour",
            "cold-brew-cans",
            "sampler",
        ]
        url_lower = url.lower()
        if any(pattern in url_lower for pattern in excluded_patterns):
            return None

        # Standardize to the format provided in the example
        if "/products/" in url:
            handle = url.split("/products/")[-1]
            return f"{self.base_url}/collections/roasted-and-ground-coffee-beans/products/{handle}"

        return url

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup | Tag:
        """Isolate the specific metaobject div for more efficient extraction."""
        if meta_div := soup.find("div", id="shopify-section-metaobject-filed"):
            return meta_div
        return soup
