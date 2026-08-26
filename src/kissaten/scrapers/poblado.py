"""Poblado Coffi scraper implementation using Shopify products.json.

Poblado Coffi (pobladocoffi.co.uk) is a roaster based in the Nantlle Valley /
Eryri (Snowdonia), North Wales. The whole-bean coffee catalogue is curated
across the ``/collections/coffee`` collection (single origins, blends, decaf,
premium and barrel-aged coffees) plus the classic single-origin and premium
feature collections that Shopify surfaces on the coffee page but which the
``/collections/coffee/products.json`` endpoint omits. All are fetched JSON-only
and canonicalised to ``/products/<handle>`` URLs.
"""

import logging

from ..ai import CoffeeDataExtractor
from . import _curl_http as httpx
from .base import WebBotAuth
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="poblado",
    display_name="Poblado Coffi",
    roaster_name="Poblado Coffi",
    website="https://pobladocoffi.co.uk",
    description="North Wales (Eryri / Nantlle Valley) speciality coffee roaster "
    "offering single origins, blends, decaf, premium and barrel-aged coffees.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class PobladoCoffiScraper(ShopifyJsonScraper):
    """Scraper for Poblado Coffi (pobladocoffi.co.uk) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize the Poblado Coffi scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Poblado Coffi",
            base_url="https://pobladocoffi.co.uk",
            products_json_urls=[
                "https://pobladocoffi.co.uk/collections/coffee/products.json",
                "https://pobladocoffi.co.uk/collections/classic-single-origin-range/products.json",
                "https://pobladocoffi.co.uk/collections/selected-premium/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Pin the store currency to the roaster's home market so Shopify's
        # geo-detected conversion (which can serve GBP-converted prices to
        # datacenter IPs) can never override it.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Whole-bean coffee only: drop gift vouchers, the variety pack
        # subscription, the explore bundle and the coffee-chocolate bar. Sampler
        # / tasting-kit products are deliberately NOT excluded - they are
        # extracted and flagged for admin review by _apply_product_flags.
        self.exclude_slugs = [
            "gift-card",
            "gift-voucher",
            "subscription",
            "bundle",
            "chocolate",
        ]

        # pobladocoffi.co.uk's edge rejects curl_cffi's default libcurl TLS
        # fingerprint with a 403, while the "chrome" impersonation profile
        # negotiates successfully (verified by probe). Rebuild the client with
        # that profile, preserving headers/auth/proxy - mirroring twoday.py.
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
            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Canonicalize Poblado product URLs to ``/products/<handle>``.

        The site serves products at ``https://pobladocoffi.co.uk/products/<handle>``
        with no collection segment. ShopifyJsonScraper builds collection-prefixed
        URLs from the products.json base, so strip the collection segment to match
        the site's canonical form (and the form stored in historical bean data).
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1]
            return f"{self.base_url}/products/{handle}"
        return url
