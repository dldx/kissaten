"""Shoebox Coffee scraper implementation."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="shoebox-coffee",
    display_name="Shoebox Coffee",
    roaster_name="Shoebox Coffee",
    website="https://shoebox.coffee",
    description="Specialty coffee roaster focused on high-quality microlots and advanced fermentations.",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="available",
)
class ShoeboxCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Shoebox Coffee (shoebox.coffee) using Shopify's products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Shoebox Coffee scraper."""
        super().__init__(
            roaster_name="Shoebox Coffee",
            base_url="https://shoebox.coffee",
            products_json_urls=["https://shoebox.coffee/collections/coffee/products.json", "https://shoebox.coffee/collections/archive/products.json"],
            scrape_product_pages=False,  # Requested to not scrape individual pages
            use_optimized_mode=False,     # Requested to not use optimized mode
            rate_limit_delay=1.0,
            max_retries=3,
            timeout=30.0,
        )
        self.exclude_slugs = ["gift-card", "wholesale", "subscription", "seasoning-beans"]

    def preprocess_product_url(self, url: str) -> str:
        """Ensure product URLs follow the /products/handle format."""
        # The base class builds the URL using the products.json URL as base.
        # For https://shoebox.coffee/collections/coffee/products.json,
        # it might create https://shoebox.coffee/collections/coffee/products/handle.
        # We want https://shoebox.coffee/products/handle.
        if "/collections/" in url:
            import re
            return re.sub(r"/collections/[^/]+/", "/", url)
        return url
