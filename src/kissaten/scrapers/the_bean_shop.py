"""The Bean Shop scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="the-bean-shop",
    display_name="The Bean Shop",
    roaster_name="The Bean Shop",
    website="https://thebeanshop.co.uk",
    description="The Bean Shop is a family-run speciality coffee roaster based in Perth, "
    "Scotland, roasting and despatching coffee from its shop at 67 George Street since "
    "1996, with a curated selection of single-origin and blend coffees.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class TheBeanShopScraper(ShopifyJsonScraper):
    """Scraper for The Bean Shop (thebeanshop.co.uk) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize The Bean Shop scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="The Bean Shop",
            base_url="https://thebeanshop.co.uk",
            products_json_urls=[
                "https://thebeanshop.co.uk/collections/coffee/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The store is based in the UK and prices are shown in GBP. Pin the
        # currency so Shopify's geo-detected market (from a datacenter IP)
        # cannot stamp a converted price onto every bean.
        self.store_currency = "GBP"
        self._currency_detected = True

        # The curated coffee collection mixes a few non-bean items into the
        # 35-product list: Moka/stovetop brewers. Subscriptions are excluded
        # by the base title-based filter ("subscription"); taster boxes
        # (.coffee-taster-box-*) are intentionally kept and flagged for review.
        self.exclude_slugs = ["moka", "stovetop"]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize The Bean Shop product URLs to the canonical form.

        The store's canonical product pages are ``/products/<handle>`` (no
        collection segment), but ShopifyJsonScraper builds collection-prefixed
        URLs from the products.json base, so strip the segment.
        """
        return url.replace("/collections/coffee/products/", "/products/")
