"""Sweet Bloom Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="sweet-bloom",
    display_name="Sweet Bloom",
    roaster_name="Sweet Bloom",
    website="https://sweetbloomcoffee.com",
    description="Centennial, Colorado specialty coffee roaster offering "
    "producer-focused single origins, including the James Hoffmann / Lucia "
    "Solis Fermentation Project.",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class SweetBloomScraper(ShopifyJsonScraper):
    """Scraper for Sweet Bloom (sweetbloomcoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Sweet Bloom scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Sweet Bloom",
            base_url="https://sweetbloomcoffee.com",
            products_json_urls=["https://sweetbloomcoffee.com/collections/coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The curated coffee collection holds only current coffee offerings
        # (including the Fermentation Project, which is kept and flagged
        # downstream). Keep a small exclude list as a safety net.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
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
        """Standardize Sweet Bloom product URLs.

        sweetbloomcoffee.com's canonical product pages are the no-collection
        form ``/products/<handle>``, so strip the ``/collections/<slug>``
        segment.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
