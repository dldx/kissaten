"""Catalyst Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="catalyst",
    display_name="Catalyst",
    roaster_name="Catalyst",
    website="https://catalyst.coffee",
    description="UK specialty coffee roaster crafting bold, experimental blends and single "
    "origins, sourcing directly at origin and showcasing funky co-ferment processing.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class CatalystScraper(ShopifyJsonScraper):
    """Scraper for Catalyst Coffee (catalyst.coffee) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Catalyst Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Catalyst",
            base_url="https://catalyst.coffee",
            products_json_urls=["https://catalyst.coffee/collections/coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The coffee collection is the master beans set (10 products, all Retail Coffee)
        # and already contains the decaf (LUCID TRANCE) and blend (e.g. COCO JAMBO) items.
        # Pin GBP and mark currency as detected so the collection-page geo-detection path
        # in _scrape_new_products cannot be overridden by a datacenter-IP market conversion.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Safety net only — the coffee collection carries no non-coffee handles today.
        # Tasting kits / samplers are NOT excluded (flag-don't-exclude); the subscribe
        # collection is simply not used as a source.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "mug",
            "apparel",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Normalize Catalyst Coffee product URLs to the canonical form.

        The store serves its canonical product URLs as ``/products/<handle>`` (no
        collection segment) — the rel=canonical tag on both the collection-prefixed
        and non-prefixed pages points at ``https://catalyst.coffee/products/<handle>``.
        The base class builds collection-prefixed URLs from the products.json base, so
        strip the ``/collections/<name>`` segment to align with the site's real URLs.
        """
        url = url.replace("/collections/coffee/products/", "/products/")
        return url
