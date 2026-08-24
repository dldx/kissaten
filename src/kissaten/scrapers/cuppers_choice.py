"""Cuppers Choice scraper implementation with Shopify JSON extraction.

Cuppers Choice (cupperschoice.coffee) is a London-based speciality coffee
roaster on Shopify. The ``.co.uk`` host 301-redirects to the canonical
``cupperschoice.coffee`` domain, which is what this scraper uses everywhere
(the site's ``rel=canonical`` links and sitemap all use ``.coffee``).

**Collections.** The umbrella ``coffee`` collection is the roaster's whole
whole-bean catalogue. Verified live it holds **14** products — exactly the
union of the ``espresso-coffee`` (11), ``filter-coffee`` (10), ``decaf-coffee``
(2) and ``omni-coffee`` (0, currently empty) collections, de-duplicated, plus a
single ``cuppers-choice-digital-gift-card``. Every one of those products is
typed ``Coffee``. Because ``coffee`` is the super-set, the leanest complete
choice is to scrape **only** ``coffee`` — no merge/dedup across four
collections is needed. (Note: ``collections.json``'s stale ``products_count``
claims 111/81/94/6/10; the authoritative counts from ``products.json`` are
14/11/10/2/0 and the live collection page also renders "14 products".)

Two non-bean items are deliberately not hit:
* ``cuppers-choice-digital-gift-card`` *is* in the ``coffee`` collection and is
  typed ``Coffee``, so it is excluded by slug (``gift-card``/``gift``).
* ``darkroom-norandino-peru-70`` is a Darkroom **chocolate** bar that Shopify
  mis-types as ``Coffee``, but it belongs to **no** collection, so scraping the
  ``coffee`` collection naturally skips it.

**Canonical.** The live product pages are the no-collection form
``/products/<handle>`` (confirmed via ``rel=canonical`` and the sitemap), so
``preprocess_product_url`` strips the injected ``/collections/coffee`` segment.

**Shape.** The Shopify ``body_html`` is rich (producer story, tasting notes,
origin, process, elevation), so the cheapest JSON-only path is used:
``scrape_product_pages=False`` with ``use_optimized_mode=True``. Currency is
pinned to GBP (the store runs Shopify Markets and may geolocate otherwise).
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="cuppers-choice",
    display_name="Cuppers Choice",
    roaster_name="Cuppers Choice",
    website="https://cupperschoice.coffee",
    description="London-based speciality coffee roaster sourcing highest-grade "
    "beans from notable producers, known for distinctive, technically "
    "processed single origins",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class CuppersChoiceScraper(ShopifyJsonScraper):
    """Scraper for Cuppers Choice (cupperschoice.coffee) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Cuppers Choice scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Cuppers Choice",
            base_url="https://cupperschoice.coffee",
            products_json_urls=[
                "https://cupperschoice.coffee/collections/coffee/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Exclude non-coffee products (the gift card, subscriptions, brewing
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

        # Pin the store currency to GBP (home market). The store runs Shopify
        # Markets and can geolocate prices to the caller's IP/Accept-Language,
        # so mark currency as already detected to stop the collection-page
        # detection from overwriting it.
        self.store_currency = "GBP"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Cuppers Choice product URLs.

        Cuppers Choice's canonical/live product pages are the no-collection
        form ``/products/<handle>`` (confirmed via ``rel=canonical``), so strip
        the ``/collections/<slug>`` segment that the products.json base URL
        injects. This keeps the scraper's URLs aligned with the site's real
        URLs.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
