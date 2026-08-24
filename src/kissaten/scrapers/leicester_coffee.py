"""Leicester Coffee House scraper implementation with Shopify JSON extraction.

Leicester Coffee House (leicestercoffeehouse.co.uk) is an independent
specialty coffee roaster and café based in Leicester, UK, on Shopify
(trading as Leicester Coffee House Company).

**Collections.** The ``coffee-beans-freshly-roasted-coffee`` collection
("Coffee Beans - Freshly Roasted Coffee") is the roaster's whole-bean
catalogue. Verified live, its ``products.json`` returns **10** products (the
collection page itself renders "10 products"); the ``collections.json``
``products_count`` field is stale — it claims 17 for this collection, same
stale-field pattern as Horsham Coffee Roaster. The site has no dedicated
blends or decaf collection (the decaf ``colombia-decaf-el-carmen`` lives
inside this one), and the ``frontpage`` collection's coffee products are a
strict subset of this collection, so the leanest complete choice is to
scrape **only** ``coffee-beans-freshly-roasted-coffee`` — no merge/dedup
across collections is needed.

The 10 products break down as 6 coffees, 1 sampler pack, and 3
subscriptions:

* 6 whole-bean coffees: ``brazil`` (Brazil - Toca da Onça),
  ``mexico-cafe-el-zapoteco-anabel-chavez-copy`` (Indonesia - Ijen
  Highlands), ``colombia-la-batea-copy`` (Peru - Cajamarca),
  ``colombia-decaf-el-carmen`` (Colombia DECAF - El Carmen),
  ``rwanda-nyabumera-1033``, ``ethiopia-halo-beriti-copy`` (Ethiopia -
  Guji Megadu). Note the ``-copy`` handles: this store duplicates product
  records and re-titles them, so the handle and title can disagree (e.g.
  handle ``mexico-cafe-el-zapoteco-anabel-chavez-copy`` is titled
  "Indonesia - Ijen Highlands"). That is fine — the handle only feeds the
  canonical URL and the title/body drive extraction.
* 1 sampler: ``single-origin-coffee-selection`` is a 4 x 250g whole-bean
  selection pack. It is **kept** (whole beans) and let the base-class
  flagger classify it as a tasting kit (``is_tasting_kit`` /
  ``requires_review``) per the KIT_REVIEW pipeline rather than being
  silently dropped — ``selection`` is deliberately NOT in
  ``exclude_slugs``.
* 3 subscriptions (``roasters-choice-subscription``,
  ``decaf-coffee-subscription``, ``single-origin-coffee-subscription``),
  excluded by the ``subscription`` slug.

Gifts (``gift-card``/``gift-pack``/``gift-wrapping-service``) render in a
cross-sell block on the collection page but are **not** members of the
collection's ``products.json`` (they live in the ``gifts`` collection), so
they never enter the pipeline.

**Canonical.** The live product pages are the no-collection form
``https://www.leicestercoffeehouse.co.uk/products/<handle>`` on the ``www``
host (confirmed via ``rel=canonical`` and ``og:url`` pointing at
``https://www.leicestercoffeehouse.co.uk/products/brazil``; the bare host
301s to ``www`` with ``canonical_host_redirection``), so
``preprocess_product_url`` strips the injected
``/collections/coffee-beans-freshly-roasted-coffee`` segment and
normalises to the www canonical host.

**Shape.** The Shopify ``body_html`` is dense (country, region, farm,
varietal, process, cup score, altitude and tasting notes in the rich
description), so the cheapest JSON-only path is used:
``scrape_product_pages=False`` with ``use_optimized_mode=True``. Currency
is pinned to GBP — the store advertises in GBP (``"currency": "GBP"`` in
the store's JSON and £ prices on the live pages) and the scraper should
never trust geo-detected prices.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="leicester-coffee",
    display_name="Leicester Coffee House",
    roaster_name="Leicester Coffee House",
    website="https://www.leicestercoffeehouse.co.uk",
    description="Independent specialty coffee roaster and café based in "
    "Leicester, UK, roasting single origins and house blends "
    "for filter and espresso",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class LeicesterCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Leicester Coffee House using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Leicester Coffee House scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Leicester Coffee House",
            base_url="https://www.leicestercoffeehouse.co.uk",
            products_json_urls=[
                "https://www.leicestercoffeehouse.co.uk/collections/coffee-beans-freshly-roasted-coffee/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Exclude non-bean products: subscriptions (3 of the collection's 10
        # products), gift cards, and brewing equipment/merch that could sneak
        # into a coffee collection. Deliberately NOT in this list:
        # tasting-kit / sampler / selection products (the 4 x 250g "Single
        # Origin Coffee Selection") are retained + flagged by the base class
        # (_apply_product_flags) rather than silently dropped.
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
            "keepcup",
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
        """Standardize Leicester Coffee House product URLs.

        The live/canonical product pages are the no-collection form
        ``/products/<handle>`` on the www host (confirmed via ``rel=canonical``
        and the bare-host 301 to www), so strip the ``/collections/<slug>``
        segment that the products.json base URL injects and normalise to the
        www canonical host.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"https://www.leicestercoffeehouse.co.uk/products/{handle}"
        return url
