"""Stables Coffee Co. scraper implementation with Shopify JSON extraction.

Stables Coffee Co. (stablescoffee.co.uk) is a UK specialty coffee roaster
with cafés in Arborfield and Buckler's Park, Berkshire. The catalogue is a
small curated range of four coffees — Bondi Blend, Didgeri Decaf, Great
Ocean Roast and Uluru — priced in GBP.

Feed selection (live discovery, 2026-08-25): the site curates no dedicated
coffee ``products.json`` collection — ``/collections/coffee``, ``/collections/beans``
and other obvious coffee slugs all return empty feeds. ``collections/all``
publishes exactly the four Coffee-type products (Bondi Blend, Didgeri Decaf,
Great Ocean Roast, Uluru) with no equipment/merch/subscription items mixed in.
A subscription or gift feed may exist behind other handles, but nothing in the
``all`` feed needs excluding, so the exclusion list is kept as a defensive
safety net only.

The ``all`` collection ``body_html`` is uniformly structured — a prose
intro plus ``Flavour Profile`` / ``Origin`` detail with per-variant price
options — so the injection-only path is used: ``scrape_product_pages=False``
with ``use_optimized_mode=True`` (the AI extracts from the Shopify JSON
context, cheapest token option; the rendered product page mirrors the same
content and adds nothing the JSON lacks).

Kit handling: none of the coffee handles carry a tasting-kit token, so the
base ``_apply_product_flags`` review pipeline is used unchanged — any future
sampler/taster product is flagged ``is_tasting_kit``/``requires_review`` into
the admin review queue rather than excluded. Only genuine non-coffee tokens
(equipment/merch/subscription) are excluded as a defensive safety net in case
the ``all`` feed ever mixes them back in; tasting-kit/sampler slugs are
deliberately absent from that list.

Canonical URLs are the no-collection ``/products/<handle>`` form (confirmed
via ``og:url`` on the live product pages), so the collection segment produced
by the products.json base is stripped in ``preprocess_product_url``.

Currency: the store is a UK roaster priced in GBP (a 250g bag lists at
£10.95), so ``store_currency`` is pinned to ``GBP`` and ``_currency_detected``
to True up front — a geo-detected market must never overwrite the home prices.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="stables",
    display_name="Stables Coffee Co.",
    roaster_name="Stables Coffee Co.",
    website="https://stablescoffee.co.uk",
    description="UK specialty coffee roaster with cafés in Arborfield and "
    "Buckler's Park, Berkshire — a compact range of Australian-inspired "
    "signature blends and a decaf roasted in small batches.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class StablesCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Stables Coffee Co. (stablescoffee.co.uk) using Shopify products.json.

    Uses ``collections/all`` because the site curates no dedicated coffee
    ``products.json`` collection (``/collections/coffee`` and friends are
    empty); ``all`` publishes exactly the four bean products.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Stables Coffee Co. scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Stables Coffee Co.",
            base_url="https://stablescoffee.co.uk",
            products_json_urls=["https://stablescoffee.co.uk/collections/all/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Stables Coffee Co. is a UK store priced in GBP. Pin the home
        # currency and mark it as detected so the collection-page
        # currency-detection path can never overwrite it with a geo-located
        # market price.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Exclude genuine non-coffee products only. The ``all`` feed
        # currently carries only the four beans, so this is purely a
        # defensive safety net in case equipment/merch/subscriptions are
        # later added. Deliberately NOT excluded: sampler / taster-pack /
        # gift-box slugs — the base class flags tasting kits
        # (flag-don't-exclude) so they land in the admin review queue rather
        # than being dropped. Note "gift-card" / "giftcard" (not a bare
        # "gift") so a future "Coffee Gift Pack" handle is not caught.
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
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Stables Coffee Co. product URLs.

        The live site canonicalizes product pages to the no-collection form
        ``/products/<handle>`` (confirmed via ``og:url``), so strip the
        ``/collections/all`` segment that the products.json base URL injects.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
