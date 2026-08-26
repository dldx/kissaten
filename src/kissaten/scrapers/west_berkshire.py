"""West Berkshire Roastery scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="west-berkshire",
    display_name="West Berkshire Roastery",
    roaster_name="West Berkshire Roastery",
    website="https://wbroast.co.uk",
    description="Berkshire-based award-winning speciality coffee roaster (wbroast.co.uk). "
    "Small-batch hand-roasted organic coffees including blends, single origins, "
    "decaf and a curated Ultimate Taster Pack.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class WestBerkshireScraper(ShopifyJsonScraper):
    """Scraper for West Berkshire Roastery (wbroast.co.uk) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize West Berkshire Roastery scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="West Berkshire Roastery",
            base_url="https://wbroast.co.uk",
            products_json_urls=[
                "https://wbroast.co.uk/collections/buy-fresh-roasted-artisan-coffee-beans-online/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Pin the store currency so Shopify Markets geo-detection can't stamp
        # converted prices onto the beans (UK roaster, all prices in GBP).
        self.store_currency = "GBP"
        self._currency_detected = True

        # The curated Coffee Beans collection is beans-only; leave the exclude
        # list empty so the Ultimate Taster Pack (coffee-bean-taster-pack) is
        # extracted and flagged for review rather than silently dropped.
        self.exclude_slugs: list[str] = []

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize West Berkshire product URLs to the canonical /products/<handle> form.

        ShopifyJsonScraper builds collection-prefixed URLs from the products.json
        base; the live site serves products at the no-collection canonical URL.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1]
            return f"{self.base_url}/products/{handle}"
        return url
