"""Sanctuary Coffee scraper implementation with Shopify JSON extraction.

Sanctuary Coffee (sanctuarycoffee.co.uk) is a UK specialty coffee roaster
pricing in GBP. The catalogue is a curated, rotating set of single origins
and blends across filter and espresso roasts, plus a decaf.

Feed selection (live discovery, 2026-08): the roaster curates a dedicated
``coffee`` collection — ``/collections/coffee/products.json`` publishes
exactly 8 Coffee-type products: Nectarine Dream (Indonesia), Peachy Keen
(Indonesia), Summer '26 (Ethiopia), Session Brew (Tanzania), Dark Espresso
(Brazil), Purple Rain (Kenya), House Espresso (Colombia) and House Decaf /
Popayan Decaf (Colombia). The other collections (110 gift-sets, 64
home/giftware) are non-bean and are not fetched at all. ``product_type`` is
empty on the feed, but every handle is a genuine bean and the collection is
coffee-only, so no coffee-vs-non-coffee filtering is needed and the default
``exclude_slugs`` (non-coffee gift/subscription tokens) is never triggered.

The ``coffee`` collection ``body_html`` is uniformly structured — tasting
notes in the lead line plus a prose origin/process/farm description — so the
injection-only path is used: ``scrape_product_pages=False`` with
``use_optimized_mode=True`` (the AI extracts from the Shopify JSON context,
cheapest token option; the rendered product page mirrors the same content and
adds nothing the JSON lacks).

Kit handling: none of the coffee handles carry a tasting-kit token, so the
base ``_apply_product_flags`` review pipeline is used unchanged — any future
sampler/taster product is flagged ``is_tasting_kit``/``requires_review`` into
the admin review queue rather than excluded. Only genuine non-coffee tokens
(gifts/subscriptions) are excluded here, as a defensive safety net in case
the feed ever mixes them back in.

Canonical URLs are the no-collection ``/products/<handle>`` form, so the
collection segment produced by the products.json base is stripped in
``preprocess_product_url``.

Currency: the store is a UK store priced in GBP (confirmed on the product
pages / feed prices), so ``store_currency`` is pinned to ``GBP`` and
``_currency_detected`` to True up front — a geo-detected market must never
overwrite the home prices.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="sanctuary-coffee",
    display_name="Sanctuary Coffee",
    roaster_name="Sanctuary Coffee",
    website="https://www.sanctuarycoffee.co.uk",
    description="UK specialty coffee roaster offering a curated, rotating range "
    "of single origins and blends with distinct espresso and filter offerings.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class SanctuaryCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Sanctuary Coffee (sanctuarycoffee.co.uk) using Shopify products.json.

    Uses the roaster's curated ``coffee`` collection rather than
    ``collections/all``, which would mix in 110 gift sets and 110
    home/giftware products.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Sanctuary Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Sanctuary Coffee",
            base_url="https://www.sanctuarycoffee.co.uk",
            products_json_urls=["https://www.sanctuarycoffee.co.uk/collections/coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Sanctuary Coffee is a UK store priced in GBP. Pin the home currency
        # and mark it as detected so the collection-page currency-detection
        # path can never overwrite it with a geo-located market price.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Exclude genuine non-coffee products only. The curated coffee
        # collection publishes only beans, so this is a defensive safety net
        # in case the feed later mixes in gifts/subscriptions/equipment.
        # Deliberately NOT excluded: sampler / taster-pack / gift-box slugs —
        # the base class flags tasting kits (flag-don't-exclude) so they land
        # in the admin review queue rather than being dropped. Note
        # "gift-card" / "giftcard" (not a bare "gift") so a future "Coffee
        # Gift Pack" handle is not caught.
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
        """Standardize Sanctuary Coffee product URLs.

        The live site canonicalizes product pages to the no-collection form
        ``/products/<handle>``, so strip the ``/collections/coffee`` segment
        that the products.json base URL injects.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
