"""Three Keys Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="three-keys-coffee",
    display_name="Three Keys Coffee",
    roaster_name="Three Keys Coffee",
    website="https://threekeyscoffee.com",
    description="Houston, Texas specialty coffee roaster blending music culture "
    "with single origins and signature blends, including the Fermentation "
    "Frequency tasting kit (James Hoffmann / Lucia Solis Fermentation Project).",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class ThreeKeysCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Three Keys Coffee (threekeyscoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Three Keys Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Three Keys Coffee",
            base_url="https://threekeyscoffee.com",
            products_json_urls=["https://threekeyscoffee.com/collections/coffee-1/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The curated coffee-1 collection holds beans plus two canned
        # ready-to-drink cold brew products; the Fermentation Frequency
        # tasting kit is kept and flagged downstream.
        self.exclude_slugs = [
            "canned-cold-brew",
            "cold-brew-cans",
            "gift-card",
            "gift",
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
