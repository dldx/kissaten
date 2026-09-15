"""Quills Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="quills-coffee",
    display_name="Quills Coffee",
    roaster_name="Quills Coffee",
    website="https://quillscoffee.com",
    description="Louisville, Kentucky specialty roaster and café group offering single-origin "
    "coffees and signature blends, including the Fermentation Project tasting set",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class QuillsCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Quills Coffee (quillscoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Quills Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Quills Coffee",
            base_url="https://quillscoffee.com",
            products_json_urls=["https://quillscoffee.com/collections/coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The curated `coffee` collection is beans-only (including the
        # [PREORDER] Fermentation Project tasting set, which is kept — it is
        # flagged as a tasting kit downstream).
        self.exclude_slugs = [
            "gift-card",
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
        """Standardize Quills Coffee product URLs.

        Quills' canonical product pages are the no-collection form
        ``/products/<handle>`` on the apex domain (no www), so strip the
        ``/collections/<slug>`` segment.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
