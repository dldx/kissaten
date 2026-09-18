"""Higher Grounds scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="higher-grounds",
    display_name="Higher Grounds",
    roaster_name="Higher Grounds",
    website="https://www.highergroundstrading.com",
    description="Traverse City, Michigan fair-trade roaster working directly with producer "
    "cooperatives in Latin America, Africa and Asia",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class HigherGroundsScraper(ShopifyJsonScraper):
    """Scraper for Higher Grounds (highergroundstrading.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Higher Grounds scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Higher Grounds",
            base_url="https://www.highergroundstrading.com",
            products_json_urls=["https://www.highergroundstrading.com/collections/all-coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The curated `all-coffee` collection keeps the James Hoffmann
        # Fermentation Project and the Trio Gift Set sampler (flagged as a
        # tasting kit downstream, not excluded). Excluded: subscriptions and
        # the Donate-A-Bag charity product (not a coffee for sale).
        self.exclude_slugs = [
            "subscription",
            "donate-a-bag",
        ]

        # Pin the home-market currency: Shopify Markets may serve
        # geo-converted prices to datacenter IPs, and the base-class
        # display-name currency lookup falls back to GBP. The home
        # currency was verified against /cart.js, so make it authoritative.
        self.store_currency = "USD"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Higher Grounds product URLs.

        Higher Grounds' canonical product pages are the no-collection form
        ``/products/<handle>``, so strip the ``/collections/<slug>`` segment.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
