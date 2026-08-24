"""Coffee Compass scraper implementation with Shopify JSON extraction.

Coffee Compass (coffeecompass.co.uk) is a UK specialty coffee roaster on
Shopify. Its site nav organises the roasted-bean catalogue into exactly four
curated collections, and the scraper mirrors that grouping with a
carnival-style multi-collection merge:

* ``roasted-origin-coffee`` — single-origin coffees (35 published beans)
* ``specialty-blends`` — Light/Medium, Mahogany and Extra Dark Ebony blends
  (incl. French Breakfast Blend)
* ``espresso-range`` — the espresso blends
* ``decaf`` — decaffeinated coffees

``collections.json`` over-reports product counts (e.g. 65 for
``roasted-origin-coffee``) because it counts unpublished items; the
``products.json`` endpoints return only published products, so the effective
union here is 53 unique products. Products appearing in more than one
collection (e.g. ``mystery-coffee-mark-18-1kg`` in both
``roasted-origin-coffee`` and ``espresso-range``) are deduplicated to the
canonical URL by the base ``discover_all_product_urls``.

The Shopify ``body_html`` carries the bean details the ``CoffeeBean`` schema
needs (tasting notes, origin, producer, elevation, process), so the cheapest
JSON-only path is used: ``scrape_product_pages=False`` with
``use_optimized_mode=True`` and no page caching. The rendered product page
adds nothing beyond JSON-LD that mirrors the product JSON.

Canonical URLs are the no-collection form ``/products/<handle>`` (confirmed
via the page ``rel=canonical`` / ``og:url``), so the collection segment built
from the products.json base is stripped in ``preprocess_product_url``.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="coffee-compass",
    display_name="Coffee Compass",
    roaster_name="Coffee Compass",
    website="https://www.coffeecompass.co.uk",
    description="UK specialty coffee roaster offering single origin coffees, "
    "espresso blends, decaf and green beans, sourced with an emphasis on "
    "direct farm relationships.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class CoffeeCompassScraper(ShopifyJsonScraper):
    """Scraper for Coffee Compass (coffeecompass.co.uk) using Shopify products.json.

    Uses the four curated collections that mirror the roaster's own site nav
    (single origins, specialty blends, espresso range, decaf) rather than
    ``collections/all``, which also mixes in tea, equipment, gift packs and
    green-bean products.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Coffee Compass scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Coffee Compass",
            base_url="https://www.coffeecompass.co.uk",
            products_json_urls=[
                "https://www.coffeecompass.co.uk/collections/roasted-origin-coffee/products.json",
                "https://www.coffeecompass.co.uk/collections/specialty-blends/products.json",
                "https://www.coffeecompass.co.uk/collections/espresso-range/products.json",
                "https://www.coffeecompass.co.uk/collections/decaf/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Coffee Compass is a UK store priced in GBP. The storefront can
        # geolocate the datacenter IP to a non-GBP market, so pin the home
        # currency and mark it as detected to skip the collection-page
        # currency-detection path.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Exclude genuine non-coffee products only. Do NOT exclude sampler /
        # taster-pack / gift-pack slugs here: the base class flags tasting
        # kits (flag-don't-exclude) so they land in the admin review queue
        # rather than being dropped. Note "gift-card" / "giftcard" (not a bare
        # "gift") so the "Coffee Compass Gift Pack" handle is not caught.
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
            "green-unroasted-beans",
            "krups-burr",
            "coffee-sacks",
            "coffeevac",
            "tea",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Coffee Compass product URLs.

        The live site canonicalizes product pages to the no-collection form
        ``/products/<handle>`` (confirmed via ``rel=canonical`` and
        ``og:url``), so strip the ``/collections/<slug>`` segment that each
        products.json base URL injects. This also makes the same product
        surfacing in multiple collections map to one canonical URL, which is
        what lets the merge + dedup count it exactly once.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url

    def postprocess_review_flags(self, bean, url: str):
        """Flag curated multi-bag samplers as tasting kits for review.

        The base tasting-kit URL/name patterns do not catch these two curated
        packs, but both are multi-coffee samplers that should go through the
        admin review queue instead of public search:

        * ``coffee-compass-gift-pack`` — 4 x 250g of two espresso blends and
          two single origins in a gift box.
        * ``coffee-compass-espresso-selection`` — build-your-own 3 x 500g
          selection of espresso blends.
        """
        if bean is not None and (
            "coffee-compass-gift-pack" in str(url) or "coffee-compass-espresso-selection" in str(url)
        ):
            bean.is_tasting_kit = True
        return bean
