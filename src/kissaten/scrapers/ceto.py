"""Ceto scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="ceto",
    display_name="Ceto",
    roaster_name="Ceto",
    website="https://ceto.coffee",
    description="Single-origin focused micro-roaster known for ultra-light 'funk' coffees and "
    "full transparency — each bag publishes varietal, altitude, process, importer and the "
    "price paid to the producer. Roasts on Sundays and ships Tuesdays.",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class CetoScraper(ShopifyJsonScraper):
    """Scraper for Ceto (ceto.coffee) using Shopify products.json.

    JSON-only extraction: the products.json ``body_html`` already carries
    tasting notes, funk rating, varietal, altitude, region, processing,
    importer and price paid, so product pages add nothing.

    Uses both the curated current ``coffee`` collection and the ``archive``
    collection (sold-out past coffees), deduplicated on the canonical
    ``/products/<handle>`` URLs.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Ceto scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Ceto",
            base_url="https://ceto.coffee",
            products_json_urls=[
                "https://ceto.coffee/collections/coffee/products.json",
                "https://ceto.coffee/collections/archive/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The curated collections are all beans (including one-off mystery
        # coffee league releases); only the coffee subscriptions need
        # exclusion. Art prints and brew gear live in separate collections
        # that we never fetch.
        self.exclude_slugs = [
            "subscription",
        ]

        # Pin the home-market currency (verified against /cart.js): Shopify
        # Markets may serve geo-converted prices to datacenter IPs.
        self.store_currency = "USD"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Ceto product URLs.

        Ceto's canonical product pages are the no-collection form
        ``/products/<handle>``, so strip the ``/collections/<slug>`` segment.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
