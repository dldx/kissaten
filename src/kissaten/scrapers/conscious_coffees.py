"""Conscious Coffee scraper implementation with Shopify JSON extraction.

Conscious Coffees (consciouscoffees.com) is a US specialty coffee roaster on
Shopify, based in Boulder, Colorado, priced in USD. It is NOT the defunct UK
"Conscious Coffees" brand — that UK entity lives at consciousspeciality.com
and is tracked under a different registry slug. Its site nav curates the
roasted-bean catalogue into a dedicated ``coffees`` collection, which the
scraper uses as its feed rather than ``collections/all`` (that mixes in merch,
gift cards, subscriptions, and equipment):

* ``coffees`` — single origins, espresso/blend/decaf offerings, and a curated
  8oz sampler pack (18 published products)

``collections.json`` lists ``coffees`` as the roaster's coffee collection; the
corresponding ``products.json`` returns only published items, so the effective
catalogue here is 18 products. The one non-roasted entry, ``organic-green-coffee``
(unroasted green beans), is excluded via ``exclude_slugs`` so the database stays
roasted-bean-only. The ``conscious-coffees-8oz-sampler-4-pack`` handle contains
``sampler``, so the base tasting-kit flagger marks it ``is_tasting_kit`` /
``requires_review`` and it lands in the admin review queue instead of being
dropped.

The Shopify ``body_html`` carries the bean details the ``CoffeeBean`` schema
needs (region, cooperative, tasting notes, roast level, post-harvest process),
so the cheapest JSON-only path is used: ``scrape_product_pages=False`` with
``use_optimized_mode=True`` and no page caching.

Canonical product URLs are the no-collection form ``/products/<handle>``
(confirmed via the page ``rel=canonical``), so the collection segment built
from the products.json base is stripped in ``preprocess_product_url``.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="conscious-coffees",
    display_name="Conscious Coffees",
    roaster_name="Conscious Coffees",
    website="https://consciouscoffees.com",
    description="US specialty coffee roaster & cooperative importer (Boulder "
    "CO)",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="available",
)
class ConsciousCoffeesScraper(ShopifyJsonScraper):
    """Scraper for Conscious Coffees (consciouscoffees.com) using Shopify products.json.

    Uses the curated ``coffees`` collection that mirrors the roaster's own site
    nav rather than ``collections/all``, which also mixes in merch, T-shirts,
    KeepCups, subscriptions and gift cards.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Conscious Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Conscious Coffees",
            base_url="https://consciouscoffees.com",
            products_json_urls=[
                "https://consciouscoffees.com/collections/coffees/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Conscious Coffee is a US store priced in USD. The storefront can
        # geolocate the datacenter IP to a non-USD market (Shopify Markets
        # serves geo-converted prices), so pin the home currency and mark it as
        # detected to skip the collection-page currency-detection path.
        self.store_currency = "USD"
        self._currency_detected = True

        # Exclude genuine non-coffee products only. Do NOT exclude sampler /
        # taster-pack slugs here: the base class flags tasting kits
        # (flag-don't-exclude) so they land in the admin review queue rather
        # than being dropped. The ``coffees`` collection already excludes
        # merch/subscription/equipment, so this list mostly guards green
        # (unroasted) beans and any stray service products.
        self.exclude_slugs = [
            "green-coffee",
            "subscription",
            "gift-card",
            "giftcard",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merch",
            "merchandise",
            "apparel",
            "mug",
            "tumbler",
            "hoodie",
            "tshirt",
            "keepcup",
            "canister",
            "capsules",
            "pods",
            "cold-brew-cans",
            "easy-pour",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Conscious Coffee product URLs.

        The live site canonicalizes product pages to the no-collection form
        ``/products/<handle>`` (confirmed via ``rel=canonical``), so strip the
        ``/collections/<slug>`` segment that the products.json base URL
        injects. This also makes a product surfacing in multiple collections
        map to one canonical URL, which is what lets the dedup count it exactly
        once.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
