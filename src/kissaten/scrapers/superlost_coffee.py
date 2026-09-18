"""Superlost Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="superlost-coffee",
    display_name="Superlost",
    roaster_name="Superlost",
    website="https://www.superlost.com",
    description="Brooklyn, New York roaster pairing experimental single origins with its "
    "Supernatural and New Light signature lines plus hyper-limited Coffee Of The Moment "
    "microlot releases",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class SuperlostCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Superlost Coffee (superlost.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Superlost Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Superlost",
            base_url="https://www.superlost.com",
            products_json_urls=["https://www.superlost.com/collections/coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Exclude the freeze-dried cold-brew concentrate squeeze bottle (not
        # whole beans). The "Coffee Of The Moment" subscription product is
        # filtered by the base class's name-based "subscription" category — a
        # substring exclude slug here would also drop the COTM microlot
        # releases whose handles start with ``coffee-of-the-moment-``.
        # Espresso blends (Supernova, Dark Matter, Cold Brew Beans) and the
        # "Dark Side" multi-bag bundle are genuine coffee and are kept.
        self.exclude_slugs = [
            "instant-coffee-concentrate",
        ]

        # Pin the home-market currency: verified against /cart.js (USD), so the
        # geo-detection cannot override it with a Shopify Markets conversion.
        self.store_currency = "USD"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Superlost product URLs.

        Superlost's canonical product pages are the no-collection form
        ``/products/<handle>``, so strip the ``/collections/<slug>`` segment.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
