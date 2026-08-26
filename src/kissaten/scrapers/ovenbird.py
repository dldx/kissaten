"""Ovenbird scraper implementation with Shopify JSON extraction.

Ovenbird (ovenbird.co.uk) is a Scottish drip-coffee roaster on Shopify. Its
site nav curates the retail roasted-bean catalogue into exactly two coffee
collections, and the scraper mirrors that grouping with a two-collection merge:

* ``single-origins`` — single-origin coffees (incl. the Colombia Madremonte
  Women's Coffee and the decaf Peru G1)
* ``blends`` — the blends and espresso-range blends (Dead Poets Society,
  North Sea Ledger, Italian Espresso, 1984, Back To Filter, Decaf Moonlight)

Together these two retail collections carry 12 published products. After
exclusion of the two non-bean items they contain, the union resolves to
**10 whole-bean coffees** — which is the store's entire roasted-bean
catalogue (confirmed against ``collections/all``). ``collections.json``
over-reports counts (it includes unpublished items), so the live
``products.json`` endpoints are the source of truth. Products surfacing in
more than one collection (e.g. ``ovenbird-gift-card``) are deduplicated to
the canonical URL by the base ``discover_all_product_urls``.

The Shopify ``body_html`` carries the bean details the ``CoffeeBean`` schema
needs (tasting notes, origin components, roast character), so the cheapest
JSON-only path is used: ``scrape_product_pages=False`` with no page caching.
``use_optimized_mode=False`` is kept for consistency with sibling scrapers;
because pages are never fetched, the injected Shopify JSON context (and the
JSON-LD ``body`` data it mirrors) is all the AI sees, which keeps token cost
low either way.

Canonical URLs are the no-collection form ``/products/<handle>`` (confirmed
via the page ``rel=canonical``), so the collection segment built from each
products.json base is stripped in ``preprocess_product_url``.

Exclusion policy
----------------
Ovenbird sells a couple of whisky barrel coffee tie-ins (``Whisky Coffee``
product type, e.g. ``the-spey-macallan``). These are spirit-cask *flavoured
coffee* products, not coffee beans — the whisky is a flavouring, not a
growing-origin fact — so they are deliberately excluded here (via
``exclude_slugs`` substring matches on their handles), rather than being
treated as flavoured beans and routed through ``_apply_product_flags``.
Curated samplers / subscription-style multi-bag packs are *not* excluded;
those flow through to ``_apply_product_flags`` so they land in the admin
review queue instead of being dropped. The gift card (``ovenbird-gift-card``)
and any wholesale / equipment items are excluded as genuine non-coffee
products.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="ovenbird",
    display_name="Ovenbird",
    roaster_name="Ovenbird",
    website="https://www.ovenbird.co.uk",
    description="Scottish specialty drip-coffee roaster offering single "
    "origin coffees and signature blends, roasted in small batches.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class OvenbirdScraper(ShopifyJsonScraper):
    """Scraper for Ovenbird (ovenbird.co.uk) using Shopify products.json.

    Uses the two curated retail coffee collections that mirror the roaster's
    own site nav (``single-origins`` and ``blends``) rather than
    ``collections/all``, which also mixes in the whisky-coffee spirit
    tie-ins, gift cards and equipment.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Ovenbird scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Ovenbird",
            base_url="https://www.ovenbird.co.uk",
            products_json_urls=[
                "https://www.ovenbird.co.uk/collections/single-origins/products.json",
                "https://www.ovenbird.co.uk/collections/blends/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Ovenbird is a UK store priced in GBP. The storefront can geolocate
        # the datacenter IP to a non-GBP market, so pin the home currency and
        # mark it as detected to skip the collection-page currency-detection
        # path.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Exclude genuine non-bean products only. "whisky"/"whiskey" and
        # "macallan" catch the Whisky Barrel Coffee tie-ins (spirit-flavoured,
        # not beans) whose handles do not otherwise reveal their nature;
        # "gift-card"/"giftcard" (not a bare "gift") catch the gift card. Do
        # NOT exclude sampler / taster-pack slugs here: the base class flags
        # tasting kits (flag-don't-exclude) so they land in the admin review
        # queue rather than being dropped.
        self.exclude_slugs = [
            "whisky",  # brew Whisky Barrel Coffee (spirit tie-in, not a bean)
            "whiskey",  # spelling variant
            "macallan",  # "The Spey — Whisky Barrel Coffee | Macallan"
            "gift-card",
            "giftcard",
            "wholesale",  # B2B wholesale catalogue
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "merch",
            "mug",
            "tumbler",
            "hoodie",
            "tshirt",
            "apparel",
            "pods",
            "capsules",
            "vbm-",  # VBM espresso machines (vbm-audrey, vbm-lollo, ...)
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Ovenbird product URLs.

        The live site canonicalizes product pages to the no-collection form
        ``/products/<handle>`` (confirmed via the page ``rel=canonical``), so
        strip the ``/collections/<slug>`` segment that each products.json base
        URL injects. This also makes the same product surfacing in multiple
        collections map to one canonical URL, which is what lets the merge +
        dedup count it exactly once.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
