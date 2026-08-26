"""Oddy Knocky Coffee scraper implementation with Shopify JSON extraction.

Oddy Knocky Coffee (oddyknockycoffee.co.uk) is a specialty coffee roaster in
Bolton, Greater Manchester. Its curated ``speciality-coffee`` collection
publishes a small rotating line of whole-bean coffees (blends plus single
origins, e.g. "House Blend", "Slam Jam", "The Notorious P.N.G.", "Faded") plus
an occasional "Espresso Gift Bundle".

Feed selection (live discovery, 2026-08-26): the curated ``speciality-coffee``
collection ``/collections/speciality-coffee/products.json`` publishes 11
products — 10 whole-bean coffees and one gift bundle (``espresso-gift-bundle``,
excluded by slug). A curated coffee collection is used rather than
``collections/all`` so wholesale duplicates, merch (``tote-bag``) and the
``coffee-club`` subscription never enter the feed.

The ``speciality-coffee`` collection ``body_html`` carries the bean details the
``CoffeeBean`` schema needs (origin, process, tasting notes, roast level), so
the injection-only path is used: ``scrape_product_pages=False`` with
``use_optimized_mode=True`` (the AI extracts from the Shopify JSON context,
the cheapest token option; the rendered product page adds nothing the JSON
lacks).

Canonical URLs are the no-collection ``/products/<handle>`` form (confirmed via
``rel=canonical`` / ``og:url`` on the live product pages), so the collection
segment produced by the products.json base is stripped in
``preprocess_product_url``.

Kit handling: none of the whole-bean handles carry a tasting-kit token, so the
base ``_apply_product_flags`` review pipeline is used unchanged — any future
sampler/taster product is flagged ``is_tasting_kit`` / ``requires_review`` into
the admin review queue rather than excluded. Only genuine gift bundles,
subscriptions and non-bean items are excluded.

Currency: the store is a UK Shopify storefront priced in GBP, so
``store_currency`` is pinned to ``GBP`` and ``_currency_detected`` to True up
front — a geo-detected market must never overwrite the home prices.

HTTP: the host 403s curl_cffi's default libcurl TLS fingerprint while the
"chrome" impersonation profile negotiates successfully, so the client is
rebuilt with ``impersonate="chrome"`` (same pattern as ``twoday.py``).
"""

import logging

from ..ai import CoffeeDataExtractor
from . import _curl_http as httpx
from .base import WebBotAuth
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="oddy-knocky",
    display_name="Oddy Knocky Coffee",
    roaster_name="Oddy Knocky Coffee",
    website="https://oddyknockycoffee.co.uk",
    description="Bolton, Greater Manchester specialty coffee roaster with a "
    "curated line of whole-bean blends and single-origin coffees.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class OddyKnockyScraper(ShopifyJsonScraper):
    """Scraper for Oddy Knocky Coffee (oddyknockycoffee.co.uk) using Shopify products.json.

    Uses the roaster's curated ``speciality-coffee`` collection rather than
    ``collections/all`` and filters out the gift bundle it publishes.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Oddy Knocky Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Oddy Knocky Coffee",
            base_url="https://oddyknockycoffee.co.uk",
            products_json_urls=[
                "https://oddyknockycoffee.co.uk/collections/speciality-coffee/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # oddyknockycoffee.co.uk's edge rejects curl_cffi's default libcurl TLS
        # fingerprint (HTTP 403 on every request), while the "chrome"
        # impersonation profile negotiates successfully. Rebuild the client
        # with that profile, preserving headers/auth/proxy.
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

        # Oddy Knocky Coffee is a UK store priced in GBP. Pin the home currency
        # and mark it as detected so the collection-page currency-detection
        # path can never overwrite it with a geo-located market price.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Exclude genuine non-bean products only. The curated speciality-coffee
        # collection publishes one gift bundle (``espresso-gift-bundle``) that
        # must be filtered. ``wholesale`` / ``subscription`` / ``club`` /
        # ``merch`` tokens are a defensive safety net in case the feed later
        # mixes such items back in. Deliberately NOT excluded: sampler /
        # taster-pack / gift-box slugs — the base class flags tasting kits
        # (flag-don't-exclude) so they land in the admin review queue rather
        # than being dropped.
        self.exclude_slugs = [
            "gift-bundle",
            "subscription",
            "gift-card",
            "giftcard",
            "wholesale",
            "club",
            "equipment",
            "brewing",
            "brew",
            "accessory",
            "merchandise",
            "merch",
            "apparel",
            "tote",
            "mug",
            "tumbler",
            "hoodie",
            "tshirt",
            "capsules",
            "pods",
        ]

        if api_key:
            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Oddy Knocky Coffee product URLs.

        The live site canonicalizes product pages to the no-collection form
        ``/products/<handle>`` (confirmed via ``rel=canonical`` and ``og:url``),
        so strip the ``/collections/speciality-coffee`` segment that the
        products.json base URL injects.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
