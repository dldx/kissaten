"""Fire and Flow Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="fire-and-flow",
    display_name="Fire and Flow",
    roaster_name="Fire and Flow",
    website="https://www.fireandflowcoffee.co.uk",
    description="UK specialty coffee roaster based in the Cotswolds, sourcing single "
    "origin coffees and house blends from farms across the globe.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class FireAndFlowScraper(ShopifyJsonScraper):
    """Scraper for Fire and Flow Coffee (fireandflow.co.uk) using Shopify products.json.

    ``fireandflow.co.uk`` 301-redirects to the canonical host
    ``www.fireandflowcoffee.co.uk``, so the canonical host is used for both the
    base URL and the products.json endpoint. The ``beans`` collection is the
    clean curated beans set: 10 products, all coffee, no equipment/pods (unlike
    ``our-coffee`` which additionally carries a ``coffee-pods`` item).
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Fire and Flow Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Fire and Flow",
            base_url="https://www.fireandflowcoffee.co.uk",
            products_json_urls=[
                "https://www.fireandflowcoffee.co.uk/collections/beans/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Pin the store currency to GBP (home market). The store serves the
        # UK market from the canonical domain, so geo-detection is not needed
        # and must not be able to override it.
        self.store_currency = "GBP"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Strip the collection segment to match the site's canonical URLs.

        ShopifyJsonScraper builds ``/collections/beans/products/<handle>`` from
        the products.json base, but the store canonicalizes every product to
        ``/products/<handle>`` (no collection segment). Strip the segment so the
        scraper's URLs match the real, canonical product pages.
        """
        return url.replace("/collections/beans/products/", "/products/")
