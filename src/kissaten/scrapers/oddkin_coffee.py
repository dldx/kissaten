"""Oddkin Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="oddkin-coffee",
    display_name="Oddkin Coffee",
    roaster_name="Oddkin Coffee",
    website="https://www.oddkincoffee.com",
    description="Bristol, UK specialty roaster focused on experimental fermentation coffees "
    "and the James Hoffmann Fermentation Project bundles",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="experimental",
)
class OddkinCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Oddkin Coffee (oddkincoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Oddkin Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Oddkin Coffee",
            base_url="https://www.oddkincoffee.com",
            products_json_urls=[
                "https://www.oddkincoffee.com/collections/speciality-coffee/products.json",
                "https://www.oddkincoffee.com/collections/decaf/products.json",
                # The Fermentation Project bundles live only in this collection.
                "https://www.oddkincoffee.com/collections/hoffman/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The curated collections contain only coffee; taster packs, sample
        # packs and the house bundle stay in and are flagged as tasting kits
        # downstream instead of being excluded.
        self.exclude_slugs = [
            "gift-card",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Oddkin Coffee product URLs.

        Oddkin's canonical product pages are the no-collection form
        ``/products/<handle>``; stripping the collection segment also dedups
        the overlapping decaf/speciality-coffee entries.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
