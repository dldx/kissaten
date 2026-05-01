"""Caravan Coffee scraper implementation with AI-powered extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="caravan-coffee",
    display_name="Caravan Coffee",
    roaster_name="Caravan Coffee",
    website="https://caravanandco.com",
    description="London-based specialty coffee roaster",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class CaravanCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Caravan Coffee using Shopify JSON API."""

    def __init__(self, api_key: str | None = None):
        """Initialize scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Caravan Coffee",
            base_url="https://caravanandco.com",
            products_json_urls=[
                "https://caravanandco.com/collections/new-coffee/products.json",
            ],
            scrape_product_pages=True,
            use_optimized_mode=True,
            # api_key is handled by the base class or ignored if not needed in __init__
        )

    def preprocess_product_url(self, url: str) -> str | None:
        """Ensure product URLs include the collection path and exclude certain slugs.

        Args:
            url: The raw product URL

        Returns:
            The standardized product URL or None if it should be excluded
        """
        excluded_patterns = ["roasters-rotation", "pods"]
        if any(pattern in url for pattern in excluded_patterns):
            return None

        if "/products/" in url and "/collections/" not in url:
            handle = url.split("/products/")[-1]
            return f"{self.base_url}/collections/new-coffee/products/{handle}"
        return url
