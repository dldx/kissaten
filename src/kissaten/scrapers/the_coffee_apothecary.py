"""The Coffee Apothecary scraper implementation with Shopify JSON extraction.

The Coffee Apothecary is a specialty coffee roaster with roastery/cafés in
Udny & Ellon, Aberdeenshire, Scotland. The canonical storefront is
``shop.thecoffeeapothecary.co.uk`` (the ``www`` subdomain is a separate brand
site). The store is Shopify-hosted.

We scrape the curated ``coffee-beans`` collection, which publishes 12
whole-bean coffees (each with 250g / 1kg variants plus the single-bag
``fermentation-project``). Every entry carries rich bean detail in the Shopify
``body_html`` (Tasting notes, Farmer, Farm, Region, Country, Variety, Process,
Altitude and a description), so the scraper is JSON-only
(``scrape_product_pages=False``) with ``use_optimized_mode=True`` — the
token-cheapest option that still captures every bean field from the injected
JSON context.

The ``coffee-beans`` collection contains only whole-bean coffee, so no slug
exclusions are needed and samplers/tasting kits (none present today) are never
silently dropped — any future one flows through ``_apply_product_flags`` into
the admin review queue.

Canonical product URLs are the no-collection ``/products/<handle>`` form
(verified via the live sitemap, which serves ``shop.thecoffeeapothecary.co.uk/
products/<handle>``), so ``preprocess_product_url`` strips the collection
segment the collection products.json base otherwise produces.

Currency is GBP — the store is UK-based and the live payload reports
``Shopify.currency = {"active":"GBP","rate":"1.0"}`` — pinned defensively so
Shopify Markets geolocation cannot stamp converted prices onto the beans.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="the-coffee-apothecary",
    display_name="The Coffee Apothecary",
    roaster_name="The Coffee Apothecary",
    website="https://shop.thecoffeeapothecary.co.uk",
    description="Scottish specialty coffee roastery with cafés in Udny and Ellon, "
    "Aberdeenshire, offering whole-bean single origins and blends",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class TheCoffeeApothecaryScraper(ShopifyJsonScraper):
    """Scraper for The Coffee Apothecary (shop.thecoffeeapothecary.co.uk) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize The Coffee Apothecary scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="The Coffee Apothecary",
            base_url="https://shop.thecoffeeapothecary.co.uk",
            products_json_urls=[
                "https://shop.thecoffeeapothecary.co.uk/collections/coffee-beans/products.json"
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The curated coffee-beans collection carries only whole-bean coffee.
        # No slug exclusions are needed, and none are applied so samplers /
        # tasting kits (if a future product appears) are never silently dropped
        # — the base _apply_product_flags flags them is_tasting_kit /
        # requires_review into the admin review queue.
        self.exclude_slugs = []

        # UK roaster — pin the home-market currency (GBP) so Shopify Markets
        # geolocation cannot stamp converted prices onto the beans.
        self.store_currency = "GBP"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Canonicalize The Coffee Apothecary product URLs to the no-collection form.

        The ``coffee-beans`` products.json base yields
        ``/collections/coffee-beans/products/<handle>``, but the site's live
        canonical product pages are the no-collection ``/products/<handle>``
        form (verified via the sitemap). Strip the collection segment so URLs
        match the canonical form (and any historical data).
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
