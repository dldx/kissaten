"""Stone Creek Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="stone-creek-coffee",
    display_name="Stone Creek Coffee",
    roaster_name="Stone Creek Coffee",
    website="https://www.stonecreekcoffee.com",
    description="Milwaukee, Wisconsin 'farm to cup' roaster offering single origins, blends, "
    "caffeine-controlled coffees and the Fermentation Project presale",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class StoneCreekCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Stone Creek Coffee (stonecreekcoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Stone Creek Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Stone Creek Coffee",
            base_url="https://www.stonecreekcoffee.com",
            products_json_urls=["https://www.stonecreekcoffee.com/collections/shop-all-coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The curated `shop-all-coffee` collection keeps the Fermentation
        # Project presale and the multi-bag caffeine-calibration kits (flagged
        # as tasting kits downstream). Excluded: Keurig-compatible pods and
        # ready-to-brew cold brew filter packs.
        self.exclude_slugs = [
            "escape-pods",
            "filter-packs",
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
        """Standardize Stone Creek Coffee product URLs.

        Stone Creek's canonical product pages are the no-collection form
        ``/products/<handle>``, so strip the ``/collections/<slug>`` segment.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
