"""Thomson's Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="thomsons",
    display_name="Thomson's Coffee",
    roaster_name="Thomson's Coffee",
    website="https://www.thomsonscoffee.com",
    description="Glasgow's oldest family-run coffee roaster, founded in 1841. "
    "Roasts a curated range of house blends and single origins in small batches.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class ThomsonCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Thomson's Coffee (thomsonscoffee.com) using Shopify products.json.

    Uses the curated ``/collections/coffee`` collection (whole-bean coffee only,
    ~20 products, some sold out). Product URLs are canonicalized to the
    no-collection ``/products/<handle>`` form that the site actually serves.
    Extraction is JSON-only (``scrape_product_pages=False``) so no product pages
    are fetched and the AI works purely on the injected Shopify context.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Thomson's Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Thomson's Coffee",
            base_url="https://www.thomsonscoffee.com",
            products_json_urls=["https://www.thomsonscoffee.com/collections/coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Pin the store currency to the home market (GBP) so the geo-detected
        # value can never override it.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Exclude non-bean/subscription products. Samplers / taster packs are
        # deliberately NOT excluded — they are extracted and flagged for review
        # via ``_apply_product_flags`` instead of being silently dropped.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "machine",
            "capsules",
            "chocolate",
            "syrup",
            "cleaning",
            "barista-kit",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Canonicalize Thomson's Coffee product URLs.

        The site serves its canonical product pages at the no-collection form
        ``https://www.thomsonscoffee.com/products/<handle>`` (the collection-
        prefixed form also resolves but is not canonical). Strip the collection
        segment that ``ShopifyJsonScraper`` builds from the products.json base.
        """
        return url.replace("/collections/coffee/products/", "/products/")
