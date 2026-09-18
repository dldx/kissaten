"""purpur Café & Kaffeerösterei scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)

_COLLECTION_SEGMENT = "/collections/frontpage"


@register_scraper(
    name="purpur-coffee",
    display_name="purpur Café & Kaffeerösterei",
    roaster_name="purpur Café & Kaffeerösterei",
    website="https://purpur.coffee",
    description="German specialty coffee roastery and café in Nuremberg offering "
    "single origin coffees and blends, including the James Hoffmann / Lucia Solis "
    "Fermentation Project tasting set.",
    requires_api_key=True,
    currency="EUR",
    country="Germany",
    status="experimental",
)
class PurpurCoffeeScraper(ShopifyJsonScraper):
    """Scraper for purpur Café & Kaffeerösterei (purpur.coffee) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize purpur scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="purpur Café & Kaffeerösterei",
            base_url="https://purpur.coffee",
            products_json_urls=["https://purpur.coffee/collections/frontpage/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The frontpage collection is the store's entire catalog and contains
        # only coffee (including the Fermentation Project tasting set, which
        # is kept and flagged downstream). No exclusions needed.
        self.exclude_slugs = []

        # Pin the home-market currency: Shopify Markets may serve
        # geo-converted prices to datacenter IPs, and the base-class
        # display-name currency lookup falls back to GBP. The home
        # currency was verified against /cart.js, so make it authoritative.
        self.store_currency = "EUR"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize purpur product URLs.

        purpur.coffee's canonical product pages are the no-collection form
        ``/products/<handle>``, so strip the ``/collections/frontpage`` segment.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
