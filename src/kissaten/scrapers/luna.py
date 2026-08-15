"""Luna Coffee scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="luna",
    display_name="Luna",
    roaster_name="Luna",
    website="https://enjoylunacoffee.com",
    description="Vancouver-based specialty coffee roaster and monthly subscription "
    "from Luna Coffee, delivering seasonal bright coffees and a physical zine.",
    requires_api_key=True,
    currency="CAD",
    country="Canada",
    status="available",
)
class LunaScraper(ShopifyJsonScraper):
    """Scraper for Luna Coffee (enjoylunacoffee.com) using Shopify products.json.

    The curated ``coffees`` collection holds only whole-bean coffees, so no
    equipment/merch filtering is needed. ``preprocess_product_url`` collapses
    the collection URL onto the canonical ``/products/<handle>`` form that the
    live site serves (no collection segment in the path).
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Luna Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Luna",
            base_url="https://enjoylunacoffee.com",
            products_json_urls=[
                "https://enjoylunacoffee.com/collections/coffees/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Luna's store currency is CAD (Vancouver, BC). Shopify geolocates
        # storefront requests by the caller's IP, so the collection page served
        # to this scraper's HTTP client advertises a localized currency (e.g.
        # GBP from a non-Canadian IP) via Shopify.currency. Mark currency as
        # already detected and force the registry CAD default so
        # _scrape_new_products doesn't overwrite it with a geolocated value.
        self.store_currency = "CAD"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Canonicalise product URLs to ``https://enjoylunacoffee.com/products/<handle>``.

        The products.json endpoint lives under ``/collections/coffees``, so the
        default URL construction yields ``/collections/coffees/products/...``.
        The live site serves the canonical ``/products/<handle>`` form, so we
        strip the collection segment here.
        """
        url = re.sub(r"/collections/[^/]+(?=/products/)", "", url)
        return url
