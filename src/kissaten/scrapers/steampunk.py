"""Steampunk Coffee Roasters scraper implementation with Shopify JSON extraction.

Steampunk Coffee Roasters (steampunkcoffee.co.uk) is a specialty coffee
roaster based in North Berwick, Scotland (UK), founded in 2018 by James
Rutledge and Josh Arnott. They roast small batches on a Giesen and source
single origins and blends directly through importers such as Minga Coffee,
priced in GBP.

Feed selection (live discovery, 2026-08-25): the roaster curates a dedicated
``freshly-roasted-coffee`` collection — ``/collections/freshly-roasted-coffee/products.json``
publishes exactly 10 products, 9 of which are coffee (product_type
``freshly roasted coffee``) and 1 non-coffee ``merchandise`` item (the
``naked-coffee-canister``). The 9 coffee products are whole beans; the only
exclusion needed is the canister. The remaining coffee set is:
colombia-pitaya-pink-bourbon, kenya-gichatha-ini-aa, guatemala-juan-rodriguez,
ecuador-ricardo-vargas-1, supreme-coffee-colombia-hermanos-burbano,
peru-simon-brown, 1kg-brazil-marco-a-guardabaxo, varietypack and
decaf-la-serrania.

The ``freshly-roasted-coffee`` collection ``body_html`` is uniformly
structured — ``<strong>`` labelled Region / Altitude / Variety / Processing /
Tasting Notes lines plus a prose farm/producer write-up — so the injection-only
path is used: ``scrape_product_pages=False`` with ``use_optimized_mode=True``
(the AI extracts from the Shopify JSON context, cheapest token option; the
rendered product page mirrors the same content and adds nothing the JSON
lacks).

Kit handling: the ``varietypack`` handle carries a sampler token and is a
curated taster pack. Per project policy it is NOT excluded — the base
``_apply_product_flags`` review pipeline flags it ``is_tasting_kit`` /
``requires_review`` into the admin review queue rather than silently dropping
it. Only the ``canister`` (merchandise) is excluded here, along with generic
non-coffee tokens as a safety net in case the collection feed ever mixes
equipment/merch back in.

Canonical URLs are the no-collection ``/products/<handle>`` form (confirmed
via ``rel=canonical`` and ``og:url`` on the live product pages), so the
collection segment produced by the products.json base is stripped in
``preprocess_product_url``.

Currency: prices are GBP (e.g. £13.00 / £48.00) and the store is UK-based, so
``store_currency`` is pinned to ``GBP`` and ``_currency_detected`` to True up
front — a geo-detected market must never overwrite the home prices.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="steampunk",
    display_name="Steampunk Coffee Roasters",
    roaster_name="Steampunk Coffee Roasters",
    website="https://www.steampunkcoffee.co.uk",
    description="North Berwick, Scotland specialty roaster crafting small-batch "
    "single origins and blends, sourced direct from producers and importers "
    "and priced in GBP.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class SteampunkCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Steampunk Coffee Roasters (steampunkcoffee.co.uk) using Shopify products.json.

    Uses the roaster's curated ``freshly-roasted-coffee`` collection, which
    excludes equipment/merch (only the canister sneaks in and is filtered).
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Steampunk Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Steampunk Coffee Roasters",
            base_url="https://www.steampunkcoffee.co.uk",
            products_json_urls=["https://www.steampunkcoffee.co.uk/collections/freshly-roasted-coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Steampunk is a UK store priced in GBP. Pin the home currency and mark
        # it as detected so the collection-page currency-detection path can
        # never overwrite it with a geo-located market price.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Exclude genuine non-coffee products only. The curated coffee
        # collection contains a single non-bean item (the canister,
        # product_type ``merchandise``); the rest of these tokens are a
        # defensive safety net in case the feed later mixes in equipment/merch.
        # Deliberately NOT excluded: sampler / taster-pack / variety-pack
        # slugs — the base class flags tasting kits (flag-don't-exclude) so
        # they land in the admin review queue rather than being dropped. Note
        # "gift-card" / "giftcard" (not a bare "gift") so a future "Coffee
        # Gift Pack" handle is not caught.
        self.exclude_slugs = [
            "canister",
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
        """Standardize Steampunk Coffee Roasters product URLs.

        The live site canonicalizes product pages to the no-collection form
        ``/products/<handle>`` (confirmed via ``rel=canonical`` and
        ``og:url``), so strip the ``/collections/freshly-roasted-coffee``
        segment that the products.json base URL injects.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
