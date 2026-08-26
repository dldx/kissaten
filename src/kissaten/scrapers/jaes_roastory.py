"""Jae's RoaStory scraper implementation with Shopify JSON extraction.

Jae's RoaStory (jaesroastory.co.uk, rebranded from "Jae's Roaster") is a UK
specialty coffee roaster. The live catalogue (researched 2026-08-24) is a
compact range: three signature espresso blends roasted light/medium — The
SciFi Blend (Light), The Fiction Blend (Medium Light), The Classics Blend
(Medium Dark) — plus a decaf, the True Crime Blend (Medium Decaffeinated).
Each bean ships as 250g / 500g / 1kg whole-bean variants, priced in GBP.

Feed selection (live discovery, 2026-08-24): the apex ``/products.json``
publishes 5 products, of which exactly one — ``hot-romance-hot-chocolate``
(product_type ``Chocolate``, titled "Hot Romance (Hot Chocolate)") — is not
coffee and is the only exclusion needed. The remaining 4 are genuine beans.
The feed is filtered to coffee only via a ``hot-chocolate`` exclude token
(matching both the handle and the title/p_type); no bean is hardcoded.

The product ``body_html`` is uniformly structured — a ``Roast Level`` line
followed by a ``Tasting Notes`` line plus a prose description — so the
injection-only path is used: ``scrape_product_pages=False`` with
``use_optimized_mode=True`` (the AI extracts from the injected Shopify JSON
context, cheapest token option; the rendered product page mirrors the same
content and adds nothing the JSON lacks).

Kit handling: none of the coffee handles carry a tasting-kit token, so the
base ``_apply_product_flags`` review pipeline is used unchanged — any future
sampler/taster product is flagged ``is_tasting_kit``/``requires_review`` into
the admin review queue rather than excluded. Only the hot-chocolate product
is excluded here, along with generic non-coffee tokens as a safety net in
case the feed ever mixes equipment/merch back in.

Canonical URLs use the no-collection ``/products/<handle>`` form (confirmed
via ``rel=canonical`` on the live product pages). Because the feed is the
apex ``/products.json`` (not a collection), the base class already builds the
canonical URL — no collection segment to strip.

Currency: the store is a UK shop priced in GBP, so ``store_currency`` is
pinned to ``GBP`` and ``_currency_detected`` to True up front — a
geo-detected market must never overwrite the home prices.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="jaes-roastory",
    display_name="Jae's RoaStory",
    roaster_name="Jae's RoaStory",
    website="https://jaesroastory.co.uk",
    description="UK specialty coffee roaster (rebranded from Jae's Roaster) with a "
    "compact, literature-themed range of espresso blends — Classics, Fiction, SciFi "
    "and a decaf — roasted to order in three bag sizes.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class JaesRoastoryScraper(ShopifyJsonScraper):
    """Scraper for Jae's RoaStory (jaesroastory.co.uk) using Shopify products.json.

    Uses the apex ``/products.json`` feed and excludes the single non-coffee
    product (a hot-chocolate) by slug/type.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Jae's RoaStory scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Jae's RoaStory",
            base_url="https://jaesroastory.co.uk",
            products_json_urls=["https://jaesroastory.co.uk/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Jae's RoaStory is a UK shop priced in GBP. Pin the home currency
        # and mark it as detected so the collection-page currency-detection
        # path can never overwrite it with a geo-located market price.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Exclude genuine non-coffee products only. The apex feed currently
        # contains a single non-bean item (hot-chocolate); the rest of these
        # tokens are a defensive safety net in case the feed later mixes in
        # equipment/merch. Deliberately NOT excluded: sampler / taster-pack /
        # gift-box slugs — the base class flags tasting kits
        # (flag-don't-exclude) so they land in the admin review queue rather
        # than being dropped. Note "hot-chocolate" (not a bare "chocolate")
        # so a future "Chocolate Milkshake Coffee" bean handle is not caught.
        self.exclude_slugs = [
            "hot-chocolate",
            "gift-card",
            "giftcard",
            "subscription",
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
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
