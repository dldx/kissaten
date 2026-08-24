"""Clifton Coffee Roasters scraper implementation with Shopify JSON extraction.

Clifton Coffee Roasters (cliftoncoffee.co.uk) is a Shopify store based in
Bristol, UK. The curated ``/collections/coffee`` ("All Coffee") products.json
carries 20 products (verified 2026-08) including Suspension Espresso, Village
Organic, E1 Project Espresso, Cadence Espresso, House Filter and a range of
single origins. The ``body_html`` is dense (producer, farm, region, process,
tasting detail), so the scraper runs JSON-only
(``scrape_product_pages=False``, ``use_optimized_mode=True``) against the
injected Shopify context — the cheapest token path.

The coffee collection also lists a few genuine non-bean items (Nespresso
capsules, branded storage tins) which are excluded via ``exclude_slugs``. Any
tasting-kit / sampler products must NOT be excluded — the base ``_apply_product_flags``
flags them instead so they land in the admin review queue.

Canonical product URLs are the no-collection form ``/products/<handle>``
(verified live: ``/products/cadence-espresso`` and
``/products/colombia-finca-las-flores-1`` both return 200). ``preprocess_product_url``
strips the ``/collections/coffee/`` segment the base injects, and some handles
carry a ``-1`` suffix (e.g. ``colombia-finca-las-flores-1``).
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="clifton",
    display_name="Clifton Coffee Roasters",
    roaster_name="Clifton",
    website="https://cliftoncoffee.co.uk",
    description="Bristol-based specialty coffee roaster known for balanced espresso "
    "blends and a rotating range of single-origin coffees",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class CliftonScraper(ShopifyJsonScraper):
    """Scraper for Clifton Coffee Roasters (cliftoncoffee.co.uk) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Clifton Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Clifton",
            base_url="https://cliftoncoffee.co.uk",
            products_json_urls=["https://cliftoncoffee.co.uk/collections/coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Pin the home-market currency. The coffee collection is GBP and the
        # products.json variants carry no currency field, so geo-detection
        # could otherwise stamp a converted currency on every bean.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Exclude genuine non-bean items that appear in the coffee collection:
        # Nespresso capsules and branded storage tins. Do NOT add tasting-kit /
        # sampler / taster-pack tokens here — those are flagged by the base
        # _apply_product_flags and land in the admin review queue instead.
        self.exclude_slugs = ["capsules", "coffee-tin"]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Strip the collection segment so product URLs are canonical.

        The base ShopifyJsonScraper builds ``/collections/coffee/products/<handle>``
        from the products.json base, but Clifton's canonical product pages are the
        no-collection form ``/products/<handle>``.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
