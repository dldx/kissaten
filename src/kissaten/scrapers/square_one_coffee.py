"""Square One Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="square-one-coffee",
    display_name="Square One Coffee",
    roaster_name="Square One Coffee",
    website="https://shop.squareonecoffee.com",
    description="Lancaster, Pennsylvania specialty coffee roaster offering "
    "single origins and signature blends, plus the James Hoffmann / Lucia Solis "
    "Fermentation Project.",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class SquareOneCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Square One Coffee (shop.squareonecoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Square One Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Square One Coffee",
            base_url="https://shop.squareonecoffee.com",
            products_json_urls=["https://shop.squareonecoffee.com/collections/coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The curated coffee collection holds only beans; exclude the eco pod
        # product (not whole-bean coffee). Keep a small safety net for
        # subscription/gift-card style products.
        self.exclude_slugs = [
            "pods",
            "subscription",
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

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Square One Coffee product URLs.

        Square One's canonical product pages are the no-collection form
        ``/products/<handle>``, so strip the ``/collections/<slug>`` segment.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
