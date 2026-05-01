"""Aviary Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="aviary",
    display_name="Aviary",
    roaster_name="Aviary",
    website="https://www.aviary.coffee",
    description="Hyper-focused specialty coffee roaster founded on the belief that coffee should be environmentally-responsible, economically sustainable, progressive and delicious.",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="available",
)
class AviaryCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Aviary Coffee (aviary.coffee) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Aviary Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Aviary",
            base_url="https://www.aviary.coffee",
            products_json_urls=[
                "https://aviary.coffee/collections/coffees/products.json",
            ],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Aviary Coffee product URLs.

        Aviary historical data uses the full collection path with www.
        """
        # Ensure we use the www version as per historical data
        url = url.replace("https://aviary.coffee", "https://www.aviary.coffee")

        # Historical data includes the collection path, so we do NOT strip it.
        # ShopifyJsonScraper generates these by default from products_json_urls metadata.
        return url

    def preprocess_product_soup(self, soup: any) -> any:
        """Limit extraction to the product metadata division for efficiency."""
        meta = soup.select_one("div.product-single__meta")
        if meta:
            logger.debug("Limiting extraction to div.product-single__meta")
            return meta
        return soup
