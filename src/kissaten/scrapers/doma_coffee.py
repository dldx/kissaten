"""DOMA Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="doma-coffee",
    display_name="DOMA Coffee",
    roaster_name="DOMA Coffee",
    website="https://www.domacoffee.com",
    description="Postcard-perfect Pacific Northwest roaster in Sandpoint, Idaho, sourcing "
    "relationship coffees with a focus on sustainability and community",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class DomaCoffeeScraper(ShopifyJsonScraper):
    """Scraper for DOMA Coffee (domacoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize DOMA Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="DOMA Coffee",
            base_url="https://www.domacoffee.com",
            products_json_urls=["https://www.domacoffee.com/collections/coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The curated `coffee` collection keeps the Fermentation Project kit and
        # every whole-bean coffee; only the instant variants of the house blends
        # are excluded (handles: carmelas-instant, deep-instant, jackie-oh-instant,
        # the-chronic-instant, plus the -instant-bulk variants).
        self.exclude_slugs = [
            "instant",
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
        """Standardize DOMA Coffee product URLs.

        DOMA's canonical product pages are the no-collection form
        ``/products/<handle>``, so strip the ``/collections/<slug>`` segment.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
