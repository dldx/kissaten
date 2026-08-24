"""Fireheart Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="fireheart",
    display_name="Fireheart",
    roaster_name="Fireheart",
    website="https://fireheartcoffee.com",
    description="UK specialty coffee roaster crafting fresh seasonal coffees from "
    "small, sustainable farms and cooperatives around the world.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class FireheartScraper(ShopifyJsonScraper):
    """Scraper for Fireheart Coffee (fireheartcoffee.com) using Shopify products.json.

    Uses the curated ``all-coffee`` beans collection (11 products) rather than
    ``collections/all`` or ``collections/coffee`` (the latter mixes in
    Nespresso-compatible pods). The collection includes the "Fireheart Flight
    Taster Pack" tasting kit, which must NOT be excluded — the base
    ``_apply_product_flags`` flags it ``is_tasting_kit``/``requires_review``
    into the admin review queue via the base ``taster-pack`` URL pattern.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Fireheart Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Fireheart",
            base_url="https://fireheartcoffee.com",
            products_json_urls=["https://fireheartcoffee.com/collections/all-coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Pin the home-market currency (GBP). Fireheart serves prices per the
        # caller's geolocated Shopify market; force our datacenter IP back to
        # GBP so geo-converted prices can't stamp onto every bean.
        self.store_currency = "GBP"
        self._currency_detected = True

        # all-coffee is a curated beans collection, but keep a light guard for
        # any stray equipment/gift products. Deliberately no taster-pack /
        # sampler patterns here — the tasting kit is flag-don't-exclude.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "merch",
            "merchandise",
            "voucher",
            "grinder",
            "mug",
            "pods",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Strip the collection segment so URLs match the site's canonical form.

        Fireheart canonicalizes to ``/products/<handle>`` (no collection
        segment), e.g. ``/products/colombia-majestic``. The base class builds
        ``/collections/all-coffee/products/<handle>`` from the products.json
        base, so remove the collection path here.
        """
        return url.replace(
            "https://fireheartcoffee.com/collections/all-coffee",
            "https://fireheartcoffee.com",
        )
