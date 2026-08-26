"""Ratdog Speciality Coffee Roaster scraper implementation with Shopify JSON extraction.

Ratdog Speciality Coffee Roaster (ratdogspecialitycoffeeroaster.com) is a UK
specialty coffee micro-roaster on Shopify focused on rare single-origin Geisha
lots and limited-release single-origin beans. The old ``ratdogcoffee.co.uk``
domain is DNS-dead; the apex ``ratdogspecialitycoffeeroaster.com`` is canonical
(www 301-redirects to the apex). The site prices in GBP.

The bean catalogue is small and curated. The site's own nav splits the
whole-bean range into three collections, and together they account for the
entire published coffee catalogue (16 products):

* ``single-origin`` — 8 single-origin beans (H1 Monte Brisas, SL28/SL34,
  Java Costa Rica, Janson 749, Kotowa Las Brujas, La Esmeralda Washed, the
  premium Geisha 15 g lot, and the premium Geisha blind-box sampler)
* ``rare-exotic`` — a strict subset of ``single-origin`` (5 rare/exotic lots
  that also appear there); harmless to fetch, the base
  ``discover_all_product_urls`` dedups them to the canonical URL.
* ``3-archive-beans-that-were-sold-out`` — 8 previously sold-out lots
  (74110 Guji, Kurume, Janson Panama, La Esmeralda Natural, Caturra,
  Geisha Village, Pacas Honduras, Milton Monroy Colombia).

The union of the three collection endpoints is 16 unique products, matching
``products.json`` (``collections/all`` equivalent) exactly. All 16 are coffee
beans — there is no equipment/merchandise/gift-card noise to filter out.

The Shopify ``body_html`` carries the bean details the ``CoffeeBean`` schema
needs (origin, producer, farm, elevation, process, tasting notes), so the
cheapest JSON-only path is used: ``scrape_product_pages=False`` with
``use_optimized_mode=True`` and no page caching.

Canonical URLs are the no-collection form ``/products/<handle>``, so the
collection segment built from each products.json base URL is stripped in
``preprocess_product_url``.

The ``premium-coffee-blind-box-sample-from-15-g`` handle carries the base
tasting-kit token ``sample``, so ``_apply_product_flags`` flags it
``is_tasting_kit`` / ``requires_review`` (flag-don't-exclude) and it lands in
the admin review queue rather than being dropped or shown to the public. No
``_get_tasting_kit_url_patterns`` override is needed.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="ratdog",
    display_name="Ratdog Speciality Coffee Roaster",
    roaster_name="Ratdog Speciality Coffee Roaster",
    website="https://ratdogspecialitycoffeeroaster.com",
    description="UK specialty coffee micro-roaster specialising in rare and "
    "exotic single-origin Geisha lots (Janson, Elida, La Esmeralda, Guji), "
    "limited releases and archived single-origin beans, sourced from "
    "celebrated farms across Panama, Colombia, Ethiopia, Honduras, Kenya and "
    "Costa Rica.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class RatdogScraper(ShopifyJsonScraper):
    """Scraper for Ratdog Speciality Coffee Roaster using Shopify products.json.

    Uses the three curated collections that mirror the roaster's own site nav
    (single origins, rare/exotic lots, archived sold-out beans) rather than
    ``collections/all``. Together they account for the entire 16-product
    coffee catalogue with no non-coffee noise.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Ratdog Speciality Coffee Roaster scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Ratdog Speciality Coffee Roaster",
            base_url="https://ratdogspecialitycoffeeroaster.com",
            products_json_urls=[
                "https://ratdogspecialitycoffeeroaster.com/collections/single-origin/products.json",
                "https://ratdogspecialitycoffeeroaster.com/collections/rare-exotic/products.json",
                "https://ratdogspecialitycoffeeroaster.com/collections/3-archive-beans-that-were-sold-out/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Ratdog is a UK store priced in GBP. The storefront can geolocate the
        # datacenter IP to a non-GBP market, so pin the home currency and mark
        # it as detected to skip the collection-page currency-detection path.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Exclude genuine non-coffee products only. The curated collections
        # already contain only beans, so this is belt-and-suspenders for the
        # rare future drift. Do NOT exclude sampler / taster / sample-box
        # slugs here: the base class flags tasting kits (flag-don't-exclude)
        # so the Geisha blind-box sample lands in the admin review queue
        # rather than being dropped. Note "gift-card" / "giftcard" (not a bare
        # "gift") so a hypothetical gift box is not caught.
        self.exclude_slugs = [
            "subscription",
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
        """Standardize Ratdog product URLs.

        The live site canonicalizes product pages to the no-collection form
        ``/products/<handle>``, so strip the ``/collections/<slug>`` segment
        that each products.json base URL injects. This also makes the same
        product surfacing in multiple collections map to one canonical URL,
        which is what lets the merge + dedup count it exactly once.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
