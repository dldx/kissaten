"""Saints of Mokha scraper implementation with Shopify JSON extraction.

Saints of Mokha (saintsofmokha.com) is the UK arm of the specialty coffee
importer/roaster best known as one of the world's leading channels for Yemeni
coffee — the site is the UK's sole winner of the 2025 Best of Yemen auction —
alongside a curated programme of single-origin lots and house blends. The
catalogue is tiny and almost entirely coffee, priced in GBP.

Feed selection (re-verified live, 2026-08): the root ``/products.json``
publishes exactly 11 products, which is authoritative and complete for the
storefront. The curated ``speciality-coffee`` collection lists only 8 and its
``products_count`` (42) is inflated by unpublished/archived products, so the
collection is not trustworthy as the catalogue source. Of the 11 published
products, 10 are genuine coffee: eight single-origin lots (Reza Nurullah
Indonesia, Edinson Argote Colombia, Banko Gotiti Ethiopia, Best of Yemen
2025, Sidney Kibet Kenya, Olina Cai China, Risaralda decaf), the 1400 house
blend, and two house espresso blends (Luna - 500g, Red Velvet - 500g). The
11th (``brew-better-coffee-at-home``) carries Shopify ``product_type``
"Coffee" but is actually the *Brew* guidebook — a genuine non-coffee item, so
it is excluded by slug. No sampler/taster-pack products are present today;
any that appear are flagged by the base ``_apply_product_flags`` review
pipeline (``is_tasting_kit``/``requires_review``) rather than excluded.

The ``body_html`` for every coffee product is uniformly structured — prose
producer/farm story plus labelled Traceability (producer < farm < region <
country), Process, Varietal/Species, Tasting Notes and altitude — so the
injection-only path is used: ``scrape_product_pages=False`` with
``use_optimized_mode=True``; the AI extracts from the Shopify JSON context
(the cheapest token option) and the rendered product page mirrors the same
content. No carousels/accordions hide additional detail.

Canonical URLs are the no-collection ``/products/<handle>`` form (confirmed
via ``rel=canonical``/``og:url`` on live product pages), which the root feed
already produces; ``preprocess_product_url`` stays as defense so the URLs
remain aligned even if a collection feed is ever substituted.

Currency: the store ships SQL ``Shopify.currency = {"active":"GBP", ...}``
on product pages and prices are stable GBP across geo probes (``*currency=US``
and non-English ``Accept-Language``) — no Shopify Markets conversion.
``store_currency`` is pinned to ``GBP`` and ``_currency_detected`` to True up
front so a geo-detected market can never overwrite the home prices.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="saints-of-mokha",
    display_name="Saints of Mokha",
    roaster_name="Saints of Mokha",
    website="https://saintsofmokha.com",
    description="UK-wing of the specialty coffee importer famed for "
    "single-origin lots, heirloom blends and a curated "
    "championing of Yemeni coffee.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class SaintsOfMokhaScraper(ShopifyJsonScraper):
    """Scraper for Saints of Mokha (saintsofmokha.com) using Shopify products.json.

    Uses the root ``/products.json`` (11 published) rather than the
    ``speciality-coffee`` collection, whose products_count includes
    unpublished/archived products.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Saints of Mokha scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Saints of Mokha",
            base_url="https://saintsofmokha.com",
            products_json_urls=["https://saintsofmokha.com/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Saints of Mokha is a UK store priced in GBP (verified stable across
        # geo/locale probes). Pin the home currency and mark it as detected so
        # the collection-page currency-detection path can never overwrite it.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Exclude genuine non-coffee products only. The root feed publishes
        # one such item — the "Brew: Better Coffee at Home" guidebook
        # (Shopify type "Coffee" but actually a book). The remaining tokens
        # are a defensive safety net in case the root feed ever mixes in
        # equipment/merch. Deliberately NOT excluded: sampler / taster-pack /
        # gift-box slugs — the base class flags tasting kits
        # (flag-don't-exclude) so they land in the admin review queue rather
        # than being dropped. Note "gift-card" / "giftcard" (not a bare
        # "gift") so a future "Coffee Gift Pack" handle is not caught.
        self.exclude_slugs = [
            "brew-better-coffee-at-home",
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
        """Standardize Saints of Mokha product URLs.

        The root ``/products.json`` feed already yields the canonical
        no-collection ``/products/<handle>`` form (confirmed via
        ``rel=canonical`` and ``og:url`` on the live product pages). This
        override is defensive: if the feed is ever switched to a collection
        ``products.json``, any ``/collections/<slug>`` segment is stripped so
        URLs stay aligned with the site's real canonical form.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
