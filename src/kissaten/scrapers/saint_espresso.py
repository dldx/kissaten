"""Saint Espresso scraper implementation with Shopify JSON extraction.

Saint Espresso (www.saintespresso.com) is a UK specialty coffee roaster
based in London. Their curated ``shop-coffee`` collection publishes a small
range of whole-bean coffees priced in GBP: the "Angel" espresso/filter/decaf
line plus Producer single origins (Wamuguma Kenya, Pink Bourbon Colombia,
Wahana Indonesia, etc).

Feed selection (live discovery, 2026-08-24): the ``shop-coffee`` collection
``/collections/shop-coffee/products.json`` publishes 16 Coffee-type products,
7 of which are 100% Compostable Nespresso-compatible capsules (``*-pods`` /
``*-pods-selection`` handles). Those capsules are excluded by slug, leaving 9
genuine whole-bean coffees. A curated coffee collection is used rather than
``collections/all`` so equipment/merch (``shop-brew-kit``,
``shop-merchandise``) never enters the feed; ``shop-subscriptions`` is empty.
The ``exclude_slugs`` below is a defensive safety net should the feed later
mix non-bean items back in.

The ``shop-coffee`` collection ``body_html`` is uniformly structured — prose
descriptions plus Origin/Producer/Variety/Process/Altitude/Notes sections — so
the injection-only path is used: ``scrape_product_pages=False`` with
``use_optimized_mode=True`` (the AI extracts from the Shopify JSON context,
cheapest token option; the rendered product page mirrors the same content and
adds nothing the JSON lacks).

Kit handling: none of the whole-bean handles carry a tasting-kit token, so the
base ``_apply_product_flags`` review pipeline is used unchanged — any future
sampler/taster product is flagged ``is_tasting_kit`` / ``requires_review`` into
the admin review queue rather than excluded.

Canonical URLs are the no-collection ``/products/<handle>`` form (confirmed
via ``rel=canonical`` / ``og:url`` on the live product pages), so the
collection segment produced by the products.json base is stripped in
``preprocess_product_url``.

Currency: the store is a UK Shopify storefront priced in GBP, so
``store_currency`` is pinned to ``GBP`` and ``_currency_detected`` to True up
front — a geo-detected market must never overwrite the home prices.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="saint-espresso",
    display_name="Saint Espresso",
    roaster_name="Saint Espresso",
    website="https://www.saintespresso.com",
    description="London-based specialty coffee roaster with a signature "
    "Angel Espresso/Filter/Decaf range alongside rotating Producer "
    "single-origin coffees.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class SaintEspressoScraper(ShopifyJsonScraper):
    """Scraper for Saint Espresso (www.saintespresso.com) using Shopify products.json.

    Uses the roaster's curated ``shop-coffee`` collection rather than
    ``collections/all`` and filters out the capsule-pod items it publishes.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Saint Espresso scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Saint Espresso",
            base_url="https://www.saintespresso.com",
            products_json_urls=[
                "https://www.saintespresso.com/collections/shop-coffee/products.json"
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Saint Espresso is a UK store priced in GBP. Pin the home currency
        # and mark it as detected so the collection-page currency-detection
        # path can never overwrite it with a geo-located market price.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Exclude genuine non-bean products only. The curated shop-coffee
        # collection publishes a set of Compostable Nespresso capsule pods
        # (handles like ``*-pods`` / ``*-pods-selection``) that must be
        # filtered. ``subscription`` / ``wholesale`` / equipment / merch
        # tokens are a defensive safety net in case the feed later mixes such
        # items back in. Deliberately NOT excluded: sampler / taster-pack /
        # gift-box slugs — the base class flags tasting kits (flag-don't-
        # exclude) so they land in the admin review queue rather than being
        # dropped.
        self.exclude_slugs = [
            "pod",
            "capsule",
            "subscription",
            "gift-card",
            "giftcard",
            "wholesale",
            "equipment",
            "brewing",
            "brew",
            "accessory",
            "merchandise",
            "merch",
            "apparel",
            # Dash-delimited so a bare "mug" cannot match a coffee handle
            # like "producer-wamuguma-kenya" (which contains "...-mug-...").
            "-mug",
            "-tumbler",
            "-hoodie",
            "-tshirt",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Saint Espresso product URLs.

        The live site canonicalizes product pages to the no-collection form
        ``/products/<handle>`` (confirmed via ``rel=canonical`` and
        ``og:url``), so strip the ``/collections/shop-coffee`` segment that the
        products.json base URL injects.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
