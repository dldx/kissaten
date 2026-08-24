"""Girls Who Grind Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="girls-who-grind",
    display_name="Girls Who Grind",
    roaster_name="Girls Who Grind",
    website="https://girlswhogrindcoffee.com",
    description="UK specialty coffee roaster with a 'Grown by Women' positioning, "
    "sourcing single-origin coffees produced and grown by women around the world.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class GirlsWhoGrindScraper(ShopifyJsonScraper):
    """Scraper for Girls Who Grind Coffee (girlswhogrindcoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Girls Who Grind Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Girls Who Grind",
            base_url="https://girlswhogrindcoffee.com",
            products_json_urls=[
                "https://girlswhogrindcoffee.com/collections/coffee/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Pin GBP: the store is UK-marketed and products.json serves no
        # currency marker, so the geo-detected value must not override.
        self.store_currency = "GBP"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Girls Who Grind product URLs to the canonical form.

        The products.json collection base yields
        ``/collections/coffee/products/<handle>``, but the site's canonical
        product pages are ``/products/<handle>`` (no collection segment), so
        the collection segment is stripped.
        """
        if "/products/" in url:
            handle = url.split("/products/", 1)[-1]
            return f"{self.base_url}/products/{handle}"
        return url
