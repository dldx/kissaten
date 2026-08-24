"""Kapow Coffee scraper implementation with Shopify JSON extraction.

Kapow Coffee (kapowcoffee.co.uk) is a Leeds-based speciality coffee roaster on
Shopify (roasting and serving since 2013). GBP, UK.

**Collections.** The curated ``coffee-beans`` collection is the roaster's whole
whole-bean catalogue. Verified live it holds **6** products — the same set the
``frontpage`` collection and ``/collections/all`` return, and the exact set of
product URLs in ``sitemap_products_1.xml``. All six are typed ``Coffee beans``
(one house blend, two DECAF, three single origins). ``collections.json``'s
``products_count`` is stale (claims 8/11); the authoritative count from
``products.json`` and the sitemap is 6. No merge across collections is needed.

**Canonical.** The live product pages are the no-collection form
``/products/<handle>`` (confirmed via ``rel=canonical``), so
``preprocess_product_url`` strips the injected ``/collections/coffee-beans``
segment.

**Shape.** The Shopify ``body_html`` is rich (tasting notes, process, variety,
altitude, origin, brewing recommendations — 1000–1500 chars per product), so the
cheapest JSON-only path is used: ``scrape_product_pages=False`` with
``use_optimized_mode=True``. Currency is pinned to GBP (confirmed live via
``meta.json`` and the product JSON; the store can geolocate otherwise).
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="kapow",
    display_name="Kapow Coffee",
    roaster_name="Kapow Coffee",
    website="https://kapowcoffee.co.uk",
    description="Leeds-based speciality coffee roaster serving coffee to all in "
    "Leeds since 2013, with a house blend, single origins and decaf",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class KapowCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Kapow Coffee (kapowcoffee.co.uk) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Kapow Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Kapow Coffee",
            base_url="https://kapowcoffee.co.uk",
            products_json_urls=[
                "https://kapowcoffee.co.uk/collections/coffee-beans/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Exclude non-coffee products (subscriptions, gift cards, brewing
        # equipment, merch). Deliberately NOT in this list: tasting-kit /
        # sampler / taster-pack products are retained + flagged by the base
        # class (_apply_product_flags) rather than silently dropped.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "brewer",
            "grinder",
            "accessory",
            "merchandise",
            "merch",
            "apparel",
            "mug",
            "tumbler",
            "hoodie",
            "tshirt",
            "capsules",
            "pods",
            "cold-brew-cans",
            "easy-pour",
            "voucher",
        ]

        # Pin the store currency to GBP (home market). Confirmed live via
        # meta.json and the Shopify product JSON. Mark currency as already
        # detected so the collection-page detection can't overwrite it.
        self.store_currency = "GBP"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Kapow Coffee product URLs.

        Kapow Coffee's canonical/live product pages are the no-collection form
        ``/products/<handle>`` (confirmed via ``rel=canonical``), so strip the
        ``/collections/<slug>`` segment that the products.json base URL
        injects. This keeps the scraper's URLs aligned with the site's real
        URLs.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
