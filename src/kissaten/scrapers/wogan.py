"""Wogan Coffee scraper implementation with Shopify JSON extraction.

Wogan Coffee (wogancoffee.com) is a family coffee roaster based in Bristol
(the premium whole-bean range, not the Cardiff bean-to-bar shop). It runs on
Shopify; the curated coffee catalogue lives on the ``/collections/all-coffee``
collection (``products.json``). Prices are listed in GBP (£).

Wogan's edge rejects curl_cffi's default libcurl TLS fingerprint (HTTP 403 on
every request) while the ``"chrome"`` impersonation profile negotiates
successfully, so the HTTP client is rebuilt with that profile.

Only whole-bean coffee products are kept: ``-coffee-pods`` products are
excluded via ``exclude_slugs``, and curated taster packs are extracted and
flagged ``is_tasting_kit``/``requires_review`` (NOT excluded) so they land in
the admin review queue rather than public search.
"""

import logging
import re

from . import _curl_http as httpx
from .base import WebBotAuth
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)

_COLLECTION_PATH_RE = re.compile(r"/collections/[^/]+/products/", re.IGNORECASE)


@register_scraper(
    name="wogan",
    display_name="Wogan Coffee",
    roaster_name="Wogan Coffee",
    website="https://wogancoffee.com",
    description="Bristol family coffee roaster with a curated whole-bean range.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class WoganScraper(ShopifyJsonScraper):
    """Scraper for Wogan Coffee (wogancoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize the Wogan Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Wogan Coffee",
            base_url="https://wogancoffee.com",
            products_json_urls=["https://wogancoffee.com/collections/all-coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Wogan prices in GBP (£). Pin the store currency so geo-detection can't
        # stamp a converted market price onto every bean.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Exclude pod / non-bean products (pod handles carry "-coffee-pods").
        # Curated taster packs are deliberately NOT excluded: they are extracted
        # and flagged is_tasting_kit/requires_review by the base class.
        self.exclude_slugs = ["coffee-pods", "pods", "capsules"]

        # wogancoffee.com's edge rejects curl_cffi's default libcurl TLS
        # fingerprint (HTTP 403 on every attempt), while the "chrome"
        # impersonation profile negotiates successfully. Rebuild the client with
        # that profile, preserving headers/auth/proxy.
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

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Wogan Coffee product URLs to the canonical form.

        The base class builds collection-prefixed URLs from the products.json
        base (e.g. ``/collections/all-coffee/products/<handle>``), but Wogan's
        real/canonical product pages are ``/products/<handle>`` (no collection
        segment). Strip the collection segment so URLs match the live site.
        """
        return _COLLECTION_PATH_RE.sub("/products/", url)
