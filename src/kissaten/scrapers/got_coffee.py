"""Got Coffee Co. scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="got-coffee",
    display_name="Got Coffee Co.",
    roaster_name="Got Coffee Co.",
    website="https://gotcoffee.co",
    description="Small Canadian roaster based in Horseshoe Valley, Ontario, offering thoughtfully "
    "sourced single-origin beans sold alongside pop-up cafe events, with free shipping "
    "within Canada on orders of 3+ bags",
    requires_api_key=True,
    currency="CAD",
    country="Canada",
    status="available",
)
class GotCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Got Coffee Co. (gotcoffee.co) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Got Coffee Co. scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Got Coffee Co.",
            base_url="https://gotcoffee.co",
            products_json_urls=["https://gotcoffee.co/collections/all/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Pin the home-market currency: the store serves CAD natively
        # (Shopify.currency = {"active": "CAD", "rate": "1.0"}), but Shopify
        # Markets could geo-convert prices for a non-Canadian caller IP.
        self.store_currency = "CAD"
        self._currency_detected = True

        # Exclude non-coffee products (subscription, merch, gift cards).
        # Tasting kits / samplers are intentionally NOT excluded — they flow
        # through with is_tasting_kit / requires_review flags.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "t-shirt",
            "tshirt",
            "apparel",
            "mug",
            "tumbler",
            "equipment",
            "brewing",
            "accessory",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Got Coffee Co. product URLs.

        The site's canonical product URLs have no collection segment
        (e.g. /products/narino-reserve-colombia), while products.json is
        fetched from /collections/all/.
        """
        return url.replace("/collections/all/products/", "/products/")
