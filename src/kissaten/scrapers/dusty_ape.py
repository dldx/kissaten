"""Dusty Ape Coffee Roastery scraper implementation with Shopify JSON extraction.

Dusty Ape Coffee Roastery & Coffee Bar (Bath Beverages Ltd, Trowbridge /
Wiltshire, UK) sells through dustyape.com — a Shopify store. Products are
beans (Single Origin / Single Estate / Coffee Blend) plus decaf, a cafetiere
tasting pack, gift certificates, subscriptions and brewing equipment.

The curated ``our-coffees`` collection advertises ~112 products but the live
``products.json`` only publishes 43, so the whole catalogue is fetched from
the root ``products.json`` and filtered to genuine coffee. The cafetiere
tasting pack (``cafetiere-tasting-pack``) ONLY appears on the root payload
(gift/taster-pack collection), so it is deliberately NOT excluded: the base
``_apply_product_flags`` flags it ``is_tasting_kit`` / ``requires_review``
and it lands in the admin review queue instead of being dropped.

Shape: the Shopify JSON ``body_html`` is thin or AI-composed soup for most
beans, while the rendered page carries a structured ``.product-short-description``
block (Tasting Notes / Origin / Why so good? / Processing / Variety) plus a
``.product-single__content-text`` narrative ("All about the coffee"). So the
scraper page-scrapes and prunes the soup to those two blocks (Apricity
pattern) — token-efficient and keeps the bean detail the JSON lacks.

Canonical URLs are the no-collection ``/products/<handle>`` form, which the
root products.json base URL already produces; ``preprocess_product_url``
defensively strips any collection segment anyway.

Currency is pinned to GBP (verified ``Shopify.currency`` active GBP on the
live payload) and ``_currency_detected`` is set in ``__init__`` so no
geo-detection can override it.
"""

import logging

from bs4 import BeautifulSoup

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="dusty-ape",
    display_name="Dusty Ape",
    roaster_name="Dusty Ape",
    website="https://dustyape.com",
    description="Independent British speciality coffee roastery and coffee bar "
    "based in Trowbridge, Wiltshire. Small-batch roasting of single origins, "
    "single estates, house blends, decaf and taster packs.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class DustyApeScraper(ShopifyJsonScraper):
    """Scraper for Dusty Ape Coffee Roastery (dustyape.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Dusty Ape scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Dusty Ape",
            base_url="https://dustyape.com",
            products_json_urls=["https://dustyape.com/products.json"],
            scrape_product_pages=True,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude only genuine non-coffee products (subscriptions, gift
        # certificates, drinkware and brewing equipment). Deliberately NOT
        # excluded: the cafetiere-tasting-pack — it is a curated tasting kit
        # and must flow through to the admin review queue (flagged by
        # _apply_product_flags), not be dropped.
        self.exclude_slugs = [
            "subscription",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "apparel",
            "mug",
            "cup",
            "tumbler",
            "hoodie",
            "shirt",
            "tshirt",
            "tote",
            "motta",
            "chemex",
            "v60",
            "hario",
            "aeropress",
            "filter-papers",
            "jug",
            "sack",
            "prepaid",
            "pay-as-you-go",
            "pay-monthly",
            "decanters",
        ]

        # Store serves GBP natively; pin defensively (geo-detected currency
        # must never override the home-market GBP prices).
        self.store_currency = "GBP"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def _get_tasting_kit_url_patterns(self) -> list[str]:
        """Add Dusty Ape's taster-pack URL token to the base kit patterns.

        The base patterns match ``sample-pack`` / ``taster-pack`` style
        handles but not ``cafetiere-tasting-pack``, so extend with the
        store's ``tasting-pack`` predecessor to ensure the caf taster pack is
        flagged and sent for admin review.
        """
        return super()._get_tasting_kit_url_patterns() + ["tasting-pack"]

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Dusty Ape product URLs to the canonical form.

        Dusty Ape's canonical/live product pages are the no-collection form
        ``/products/<handle>`` (verified live; returns HTTP 200). The root
        products.json base URL already yields that form; this is a defensive
        normalization in case a collection URL ever appears.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Prune the product page to the bean-detail blocks for the AI.

        Dusty Ape renders the structured profile (Tasting Notes, Origin,
        Processing, Variety) in ``div.product-short-description`` and the
        longer "All about the coffee" narrative in
        ``div.product-single__content-text``. Keeping only these two blocks
        strips the header/footer/equipment chrome and the mass of page HTML,
        which keeps the AI extraction cheap while still passing every bean
        field the Shopify JSON lacks.

        We build a new minimal soup WITH a body: ShopifyJsonScraper injects
        the Shopify JSON context (name/price/variants) at the top of
        ``soup.body`` AFTER this hook returns, so keeping a valid body
        preserves that data.
        """
        parts = []
        short_desc = soup.select_one("div.product-short-description")
        if short_desc:
            parts.append(short_desc)
        content_text = soup.select_one("div.product-single__content-text")
        if content_text:
            parts.append(content_text)

        if not parts:
            return soup

        minimal = BeautifulSoup("<html><head></head><body></body></html>", "html.parser")
        for part in parts:
            minimal.body.append(part)
        return minimal
