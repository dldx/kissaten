"""Horsham Coffee Roaster scraper implementation with Shopify JSON extraction.

Horsham Coffee Roaster (horshamcoffeeroaster.co.uk) is an independent
specialty coffee roaster based in Horsham, West Sussex, UK, on Shopify.
The store is heavily weighted towards brewing equipment (grinders, machines,
scales, brew gear), so the collection choice below deliberately avoids every
equipment collection.

**Collections.** The ``coffee-beans`` collection ("Coffee Beans - Freshly
Roasted Coffee Beans") is the roaster's whole whole-bean catalogue. Verified
live, its ``products.json`` returns **17** products — the exact superset of the
six curated bean collections (``coffee-blends`` 5, ``single-origin-coffee-beans``
12, ``filter-coffee-beans`` 10, ``espresso-coffee-beans`` 8,
``decafcoffeebeans`` 1): the union of those six is 16 unique handles, and
``coffee-beans`` is that union plus a single ``workhorse-blend-coffee-pods``
entry. (The ``collections.json`` ``products_count`` field is stale — it claims
20 for ``coffee-beans`` while the live collection page renders "17 products"
and ``products.json`` returns 17.) Because ``coffee-beans`` is the super-set,
the leanest complete choice is to scrape **only** ``coffee-beans`` — no
carnival merge/dedup across six collections is needed.

Two non-bean items inside ``coffee-beans`` are excluded by slug:
* ``workhorse-blend-coffee-pods`` is a Nespresso-compatible **capsule** product
  (typed ``Capsules``). Pods are a separate brewing format, not whole beans,
  and the base class's name/URL exclusions do **not** cover them, so they must
  be excluded here (``pods``/``capsules``).
* ``coffee-of-the-month-subscription`` is a subscription (typed ``Coffee`` but
  a recurring service), excluded by ``subscription``.

The two "Selection" packs (``coffee-blend-selection``,
``single-origin-coffee-selection``) are 4 x 250g whole-bean coffee samplers —
kept (whole beans), per the KIT_REVIEW pipeline they are extracted and let the
base-class flagger classify them rather than being silently dropped.

Everything else in the store (grinders, espresso machines, scales, kettles,
subscriptions, gift cards, merch) lives outside ``coffee-beans`` and is never
fetched.

**Canonical.** The live product pages are the no-collection form
``/products/<handle>`` on the ``www`` host (confirmed via ``rel=canonical``
pointing at ``https://www.horshamcoffeeroaster.co.uk/products/supernova``; the
bare host 302s to ``www``), so ``preprocess_product_url`` strips the injected
``/collections/coffee-beans`` segment and normalises to the www canonical host.

**Shape.** The Shopify ``body_html`` is dense (tasting notes, process, origin,
varietal, elevation in the rich description), so the cheapest JSON-only path is
used: ``scrape_product_pages=False`` with ``use_optimized_mode=True``. Currency
is pinned to GBP — the store advertises in GBP (``Shopify.currency = "GBP"``)
and the scraper should never trust geo-detected prices.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="horsham-coffee",
    display_name="Horsham Coffee Roaster",
    roaster_name="Horsham Coffee Roaster",
    website="https://www.horshamcoffeeroaster.co.uk",
    description="Independent specialty coffee roaster based in Horsham, West "
    "Sussex, UK, roasting single origins and house blends for "
    "filter and espresso",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class HorshamCoffeeRoasterScraper(ShopifyJsonScraper):
    """Scraper for Horsham Coffee Roaster using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Horsham Coffee Roaster scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Horsham Coffee Roaster",
            base_url="https://www.horshamcoffeeroaster.co.uk",
            products_json_urls=[
                "https://www.horshamcoffeeroaster.co.uk/collections/coffee-beans/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Exclude non-bean products: capsules/pods (separate brewing format,
        # not covered by the base class exclusions), subscriptions, gift cards,
        # and brewing equipment that could sneak into the coffee collection.
        # Deliberately NOT in this list: tasting-kit / sampler / taster-pack
        # products (incl. the "Selection" 4-bag packs) are retained + flagged
        # by the base class (_apply_product_flags) rather than silently dropped.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "brewer",
            "grinder",
            "machine",
            "scales",
            "kettle",
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

        # Pin the store currency to GBP (home market). The store advertises in
        # GBP, and pinning stops the geo-detected value (which Shopify Markets
        # can serve based on the caller's IP/Accept-Language) from overriding.
        self.store_currency = "GBP"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Horsham Coffee Roaster product URLs.

        The live/canonical product pages are the no-collection form
        ``/products/<handle>`` on the www host (confirmed via ``rel=canonical``
        and the bare-host 302 to www), so strip the ``/collections/<slug>``
        segment that the products.json base URL injects and normalise to the
        www canonical host. Overlapping collections therefore merge onto a
        single URL and are never duplicated.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"https://www.horshamcoffeeroaster.co.uk/products/{handle}"
        return url
