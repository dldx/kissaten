"""Potterbeans scraper implementation with Shopify JSON extraction.

Potterbeans (potterbeans.coffee, canonical; potterbeans.co.uk redirects 301)
is a UK specialty coffee roaster on Shopify. The site's curated ``all-coffee``
collection (``/collections/all-coffee/products.json``) carries the roasted-bean
catalogue — 43 published products, 40 of them typed ``Coffee`` and 3 typed
``coffee``. The other coffee collections (``single-origin-coffee-beans``,
``coffee-blends``, ``shipped-by-sail``) are subsets of ``all-coffee``, so the
scraper uses ``all-coffee`` alone rather than merging overlapping collections.

The two lowercase-``coffee`` subscription products (``speciality-coffee-tins-
subscription``, ``coffee-of-the-month``) are genuine recurring-subscription
items and are excluded. The ``gift-box-of-5-coffee-tins`` sampler is a real
coffee tasting set and is kept; the base ``_apply_product_flags`` catches its
``gift-box`` URL and flags it ``is_tasting_kit``/``requires_review`` so it lands
in the admin review queue rather than public search. Curated multi-bag twin
packs are likewise flagged for review via ``postprocess_review_flags``.

The Shopify ``body_html`` carries the bean details the ``CoffeeBean`` schema
needs (tasting notes, origin, producer, elevation, process), so the cheapest
JSON-only path is used: ``scrape_product_pages=False`` with
``use_optimized_mode=True`` and no page caching.

Canonical product URLs are the no-collection form ``/products/<handle>``, so
the collection segment built from the products.json base is stripped in
``preprocess_product_url``.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="potterbeans",
    display_name="Potterbeans Coffee",
    roaster_name="Potterbeans Coffee",
    website="https://potterbeans.coffee",
    description="UK specialty coffee roaster based in Cornwall offering single "
    "origin coffees, espresso blends and decaf, including wood-fired and "
    "shipped-by-sail selections plus curated tasting packs.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class PotterbeansScraper(ShopifyJsonScraper):
    """Scraper for Potterbeans (potterbeans.coffee) using Shopify products.json.

    Uses the curated ``all-coffee`` collection (which is the union of the
    roaster's single-origin, blend and shipped-by-sail coffee collections)
    rather than ``collections/all``, which would mix in pottery, tableware,
    gifts and equipment.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Potterbeans scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Potterbeans Coffee",
            base_url="https://potterbeans.coffee",
            products_json_urls=[
                "https://potterbeans.coffee/collections/all-coffee/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Potterbeans is a UK store priced in GBP. The storefront can
        # geolocate the datacenter IP to a non-GBP market, so pin the home
        # currency and mark it as detected to skip the collection-page
        # currency-detection path.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Exclude genuine non-coffee / recurring-subscription products only.
        # Do NOT exclude the gift-box or twin-pack tasting samplers here: the
        # base class flags tasting kits (flag-don't-exclude) so they land in
        # the admin review queue rather than being dropped. Note "gift-card" /
        # "giftcard" (not a bare "gift") so the "Gift Box of 5 Coffee Tins"
        # sampler handle is not caught.
        self.exclude_slugs = [
            "subscription",
            "coffee-of-the-month",
            "gift-card",
            "giftcard",
            "wholesale",
            "equipment",
            "brewing",
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
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Potterbeans product URLs.

        The live site canonicalizes product pages to the no-collection form
        ``/products/<handle>``, so strip the ``/collections/all-coffee`` segment
        that the products.json base URL injects. Products surfacing in multiple
        collections map to one canonical URL, letting the merge + dedup count
        each exactly once.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url

    def postprocess_review_flags(self, bean, url: str):
        """Flag curated multi-bag twin packs as tasting kits for review.

        Potterbeans sells several ``*-twin-pack`` handles that bundle two
        distinct coffees in one box (e.g. ``anaerobic-and-super-natural-twin-
        pack``, ``co-ferment-speciality-twin-pack``, ``east-timor-twin-pack``).
        These are multi-coffee samplers that should go through the admin
        review queue instead of public search.
        """
        if bean is not None and "-twin-pack" in str(url):
            bean.is_tasting_kit = True
        return bean
