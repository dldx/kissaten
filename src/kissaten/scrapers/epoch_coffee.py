"""Epoch Chemistry scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="epoch-coffee",
    display_name="Epoch Chemistry",
    roaster_name="Epoch Chemistry",
    website="https://epoch.coffee",
    description="Specialty coffee roaster and cafe based in Moncton, New Brunswick, Canada, "
    "known for its numbered experimental coffee series (Epoch 3, 6, 9, 12 and rare Epoch X releases)",
    requires_api_key=True,
    currency="CAD",
    country="Canada",
    status="available",
)
class EpochCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Epoch Chemistry (epoch.coffee) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Epoch Chemistry scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Epoch Chemistry",
            base_url="https://epoch.coffee",
            products_json_urls=[
                "https://epoch.coffee/collections/for-website-all-coffee/products.json",
                "https://epoch.coffee/collections/nicks-picks/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The curated collections only contain coffee (beans, instant coffee and a
        # coffee bundle), so no slug exclusions are needed. Tasting-kit/sampler
        # products are intentionally kept and flagged by the base class instead.
        self.exclude_slugs = []

        # Currency geolocation guard: the store serves Canada | CAD by default
        # (confirmed on the rendered site), so pin the home currency up front and
        # prevent any geo-converted value from overriding it.
        self.store_currency = "CAD"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Epoch Chemistry product URLs.

        The site's canonical product pages are /products/<handle> (no collection
        segment), while products.json collection URLs would produce
        /collections/<name>/products/<handle>. Strip the collection segment to
        match the real site URLs and dedupe across the two collections.
        """
        if "/collections/" in url and "/products/" in url:
            base = url.split("/collections/")[0]
            handle = url.rsplit("/products/", 1)[1]
            return f"{base}/products/{handle}"
        return url
