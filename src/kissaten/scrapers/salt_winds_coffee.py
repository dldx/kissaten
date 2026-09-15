"""Salt Winds Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="salt-winds-coffee",
    display_name="Salt Winds Coffee",
    roaster_name="Salt Winds Coffee",
    website="https://saltwindscoffee.com",
    description="Canadian specialty coffee roaster in Douglas, New Brunswick, "
    "known for its ocean-air infused and flavoured coffee line-up alongside "
    "single origins and blends.",
    requires_api_key=True,
    currency="CAD",
    country="Canada",
    status="experimental",
)
class SaltWindsCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Salt Winds Coffee (saltwindscoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Salt Winds Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Salt Winds Coffee",
            base_url="https://saltwindscoffee.com",
            products_json_urls=["https://saltwindscoffee.com/collections/shop-all-coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # shop-all-coffee contains only coffee (including flavoured coffees,
        # bundles, taster packs and the Fermentation Project bundle, which are
        # kept and flagged downstream). Keep a minimal exclude list as a
        # safety net; avoid aggressive keywords like "cap"/"tee" that would
        # false-positive on handles like "captains-blend"/"privateers".
        self.exclude_slugs = [
            "gift-card",
            "gift",
            "sticker",
        ]

        # Pin the home-market currency: Shopify Markets may serve
        # geo-converted prices to datacenter IPs, and the base-class
        # display-name currency lookup falls back to GBP. The home
        # currency was verified against /cart.js, so make it authoritative.
        self.store_currency = "CAD"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
