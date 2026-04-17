"""Archetype Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="axil-coffee",
    display_name="Axil Coffee",
    roaster_name="Axil Coffee",
    website="https://axilcoffee.com.au",
    description="Coffee roaster based in Melbourne, Australia with a focus on making exceptional coffee accessible to the community.",
    requires_api_key=True,
    currency="USD",
    country="Australia",
    status="available",
)
class AxilCoffeeScraper(ShopifyJsonScraper):
    """Scraper using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Axil Coffee",
            base_url="https://axilcoffee.com.au",
            products_json_urls=[
                "https://axilcoffee.com.au/collections/coffee/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )
        # Exclude subscription products or other non-coffee items
        self.exclude_slugs = ["subscription", "drip-bag", "bundle", "pods", "cascara", "gift-card"]
