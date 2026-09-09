"""Roasti Coffee Co. scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="roasti",
    display_name="Roasti Coffee Co.",
    roaster_name="Roasti Coffee Co.",
    website="https://roasti.ca",
    description="Specialty coffee roaster and coffee bar in Sherwood Park, Alberta, Canada, "
    "offering single origins and blends alongside classic and exotic sampler packs, "
    "with direct sourcing spotlighted via partner farms such as Fazenda Samambaia (Brazil)",
    requires_api_key=True,
    currency="CAD",
    country="Canada",
    status="available",
)
class RoastiScraper(ShopifyJsonScraper):
    """Scraper for Roasti Coffee Co. (roasti.ca) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Roasti Coffee Co. scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Roasti Coffee Co.",
            base_url="https://roasti.ca",
            products_json_urls=["https://roasti.ca/collections/coffee-beans/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The curated coffee-beans collection only contains coffee (single origins,
        # blends, instant packets, and curated sampler/taster kits). No slug
        # exclusions are needed; tasting-kit/sampler products are intentionally
        # kept and flagged is_tasting_kit/requires_review by the base class.
        self.exclude_slugs = []

        # Currency geolocation guard: the store serves Canada | CAD by default
        # (confirmed in Shopify.currency on the rendered site), so pin the home
        # currency up front and prevent any geo-converted value from overriding it.
        self.store_currency = "CAD"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Roasti product URLs.

        The site's canonical product pages are /products/<handle> (no collection
        segment, as linked from the storefront), while the products.json
        collection URL would produce /collections/coffee-beans/products/<handle>.
        Strip the collection segment to match the real site URLs.
        """
        if "/collections/" in url and "/products/" in url:
            base = url.split("/collections/")[0]
            handle = url.rsplit("/products/", 1)[1]
            return f"{base}/products/{handle}"
        return url
