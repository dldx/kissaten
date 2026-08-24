"""Danelaw Coffee scraper implementation with Shopify JSON extraction.

Danelaw Coffee (danelawcoffee.co.uk) is a Yorkshire specialty coffee roaster
on Shopify. The store nav organises the roasted-bean catalogue into
per-brew-method collections, and the scraper collapses them onto a single
curated umbrella collection:

* ``all-coffee`` -- "Speciality Coffee Beans - Award Winning, Freshly
  Roasted": the store's own curated *all coffee* umbrella collection
  (28 published products when verified). It is a superset of every
  per-brew-method subset -- ``filter``, ``espresso``, ``decaf`` and
  ``great-taste-award-winners`` all contain only products already present in
  ``all-coffee`` (verified live: 0 missing products). ``collections.json`` over-reports counts (45 for ``all-coffee``)
  because it counts unpublished items / multi-collection memberships; the
  ``products.json`` endpoints return only published products (28) -- the same
  over-reporting pattern seen in the Coffee Compass build.

Because the umbrella is a superset of every subset, a single
``all-coffee`` products.json scrape is both cheaper and complete -- there is
no need to merge ``filter`` / ``espresso`` / ``decaf`` / ``great-taste``.

Canonical URLs are the no-collection form ``/products/<handle>`` (confirmed
via the page ``rel=canonical`` and ``og:url``), so the collection segment built
from the products.json base is stripped in ``preprocess_product_url``. The
``danelaw.coffee`` and ``www.danelawcoffee.co.uk`` hosts both 301 to the
canonical ``https://danelawcoffee.co.uk`` host used here.

The Shopify ``body_html`` carries the bean details the ``CoffeeBean`` schema
needs (tasting notes, origin region, altitude, process, farm/source stories),
so the cheapest JSON-only path is used: ``scrape_product_pages=False`` with
``use_optimized_mode=True`` and no page cache. The rendered product page adds
mostly JSON-LD that mirrors the product JSON.

A note on "Bjorn Speciality Coffee": Danelaw's store nav also contains a
``bjorn-speciality-coffee`` collection for the coffees served at Björn, the
roaster's own Holmfirth coffee shop. It is *not* a second roaster -- products
named/vendored "Björn Speciality Coffee" (e.g. ``red-panda-*``,
``blend-necessities-*``, ``brown-ben-*``, ``gasharu-*``, ``ethiopia-banko-*``,
``brazil-*``) are freshly roasted by Danelaw, and that collection is a subset
of ``all-coffee`` (verified live). So it is not merged-in separately and not
excluded: its products are already covered by the umbrella collection.

Curated 4x250g multi-bag bundles (``espresso-explorer-pack-2026-4x250g`` and
``nott-coffee-by-danelaw-decaf-discovery-4x250g``) are tasting-kit style
samplers: the base URL/name kit patterns do not catch the word "pack"/"box
sample" in their handles, so they are flagged ``is_tasting_kit`` (and thus
``requires_review``) explicitly in ``postprocess_review_flags`` instead of
being silently public or dropped. Only genuine equipment/services
(subscriptions, gift cards) are excluded.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="danelaw",
    display_name="Danelaw",
    roaster_name="Danelaw",
    website="https://danelawcoffee.co.uk",
    description="Yorkshire specialty coffee roaster offering award-winning "
    "espresso, filter and decaf coffees, freshly roasted in small batches and "
    "shipped across the UK.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class DanelawScraper(ShopifyJsonScraper):
    """Scraper for Danelaw Coffee (danelawcoffee.co.uk) using Shopify products.json.

    Uses the single curated umbrella collection ``all-coffee``, which is a
    published superset of every per-brew-method subset collection (filter,
    espresso, decaf, great-taste, bjorn-specialty) -- verified live with zero
    products missing from the umbrella.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize the Danelaw scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment
                variable.
        """
        super().__init__(
            roaster_name="Danelaw",
            base_url="https://danelawcoffee.co.uk",
            products_json_urls=[
                "https://danelawcoffee.co.uk/collections/all-coffee/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Danelaw is a UK store priced in GBP. The storefront can geolocate the
        # datacenter IP to a non-GBP market, so pin the home currency and mark
        # it as detected to skip the collection-page currency-detection path.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Exclude genuine non-coffee products only. Do NOT exclude sampler /
        # taster-pack / gift-pack slugs here: the base class flags tasting
        # kits (flag-don't-exclude) so they land in the admin review queue
        # rather than being dropped. Note "gift-card" / "giftcard" (not a bare
        # "gift") so no coffee handle is caught accidentally.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "giftcard",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merch",
            "apparel",
            "mug",
            "tumbler",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Danelaw product URLs.

        The live site canonicalizes product pages to the no-collection form
        ``/products/<handle>`` (confirmed via ``rel=canonical`` and
        ``og:url``), so strip the ``/collections/<slug>`` segment that each
        products.json base URL injects. This also makes products appearing in
        multiple collections map to one canonical URL, which is what lets the
        umbrella scrape count each product exactly once.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url

    def postprocess_review_flags(self, bean, url: str):
        """Flag curated 4x250g sampler bundles as tasting kits for review.

        The base tasting-kit URL/name patterns do not catch these two handles
        (neither carries a "pack/sample/taster" token the base list knows),
        but both are multi-bag coffee bundles that should go through the admin
        review queue instead of straight to public search:

        * ``espresso-explorer-pack-2026-4x250g`` -- Award-Winning Espresso
          Explorer Pack 2026 (4 x 250g tasting box of espresso blends).
        * ``nott-coffee-by-danelaw-decaf-discovery-4x250g`` -- Decaf Discovery
          4 x 250g box across the decaf range.
        """
        if bean is not None and (
            "espresso-explorer-pack" in str(url) or "decaf-discovery-4x250g" in str(url)
        ):
            bean.is_tasting_kit = True
        return bean
