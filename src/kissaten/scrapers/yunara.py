"""Yunara Coffee scraper implementation with Shopify JSON extraction.

Yunara Coffee (yunara.coffee) is a micro-roastery based in Swansea, Wales
(registered office Mumbles, Swansea). The checklist entry "Yunnara" is a
misspelling of Yunara.

The curated ``/collections/coffee`` products.json carries exactly 8
whole-bean coffees (verified 2026-08): Guayaba | Natural Blend | Colombia,
Ñuu Davii | Washed Blend | Mexico, JB Coffee | Liberica Purple Honey |
Indonesia, Gitwe Hill | Natural Bourbon | Burundi, Gundikhan Estate |
Chandragiri | India, Bolney Reinoso | Washed Gesha | Colombia, Ivan Sebay |
Washed Pink Bourbon | Colombia, and Los Nogales | Caturra Decaf | Colombia.
The ``body_html`` is dense (origin country/region, producer, process,
variety and tasting notes), so the scraper runs JSON-only
(``scrape_product_pages=False``, ``use_optimized_mode=True``) against the
injected Shopify context — the cheapest token path. No product-page
scraping means no carousel/accordion concern.

The store also sells espresso/filter subscriptions (``/collections/subscriptions``:
``drip-sub-for-filter`` and ``espresso-sub``) plus workshops/events, none of
which live in the curated coffee collection. ``exclude_slugs`` is kept as a
defensive filter in case non-bean items are added to the coffee collection,
but tasting-kit / sampler / taster-pack tokens are deliberately NOT excluded —
the base ``_apply_product_flags`` flags those instead so they land in the
admin review queue.

Canonical product URLs are the no-collection form ``/products/<handle>``
(verified live: ``/products/guayaba-natural-blend-colombia`` returns 200).
``preprocess_product_url`` strips the ``/collections/coffee/`` segment the
base injects.

The store is priced in GBP (United Kingdom). The products.json variants carry
no currency field, so currency is pinned to GBP and geo-detection is disabled
so Shopify Markets can't stamp a converted presentment currency on the beans.
"""

import logging

from . import _curl_http as httpx
from .base import WebBotAuth
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="yunara",
    display_name="Yunara Coffee",
    roaster_name="Yunara Coffee",
    website="https://yunara.coffee",
    description="Swansea (Wales) micro-roastery sourcing single-origin and blended "
    "coffees, roasted in-house and shipped as whole beans or via espresso/filter "
    "subscriptions.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class YunaraCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Yunara Coffee (yunara.coffee) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Yunara Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Yunara Coffee",
            base_url="https://yunara.coffee",
            products_json_urls=["https://yunara.coffee/collections/coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Pin the home-market currency. The coffee collection is priced in GBP and
        # the products.json variants carry no currency field, so geo-detection
        # could otherwise stamp a converted presentment currency on every bean.
        self.store_currency = "GBP"
        self._currency_detected = True

        # yunara.coffee's edge rejects curl_cffi's default libcurl TLS
        # fingerprint (403 on products.json), while the "chrome" impersonation
        # profile negotiates successfully. Rebuild the client with that profile,
        # preserving headers/auth/proxy (mirrors twoday.py).
        proxy_url = self.https_proxy or self.http_proxy
        client_kwargs: dict = {
            "headers": self.headers,
            "timeout": self.timeout,
            "auth": WebBotAuth(self),
            "impersonate": "chrome",
        }
        if proxy_url:
            client_kwargs["proxy"] = proxy_url
        self.client = httpx.AsyncClient(**client_kwargs)

        # Defensive exclude list for any non-bean items added to the curated coffee
        # collection (subscriptions, gift cards, equipment, brewing gear, merch).
        # Do NOT add tasting-kit / sampler / taster-pack tokens here — those are
        # flagged by the base _apply_product_flags and land in the admin review
        # queue instead of being dropped.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "giftcard",
            "gift",
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
            "tea",
            "matcha",
            "kettle",
            "grinder",
            "v60",
            "aeropress",
            "hario",
            "filters",
            "paper",
            "dripper",
            "brewer",
            "scale",
            "workshop",
            "event",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Strip the collection segment so product URLs are canonical.

        The base ShopifyJsonScraper builds ``/collections/coffee/products/<handle>``
        from the products.json base, but Yunara's canonical product pages are the
        no-collection form ``/products/<handle>``.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
