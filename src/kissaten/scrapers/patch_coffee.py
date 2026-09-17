"""Patch Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="patch-coffee",
    display_name="Patch",
    roaster_name="Patch",
    website="https://patchcoffee.shop",
    description="Small-batch US coffee roaster on Shopify (patchcoffee.shop); store currently "
    "unreachable at authoring time (TLS handshake refused by the Shopify edge for both the "
    "custom domain and its myshopify handle, indicating a paused/unmapped store)",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class PatchCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Patch Coffee (patchcoffee.shop) using Shopify products.json.

    Platform diagnosis (2026-09-16): the domain resolves to Shopify's edge
    (23.227.38.66) but every route fails:

    - ``https://patchcoffee.shop/`` → TLS handshake failure (SSL alert 40)
      from plain curl, curl_cffi (Chrome impersonation), and Playwright
      (``ERR_SSL_VERSION_OR_CIPHER_MISMATCH``). A third-party fetcher
      (r.jina.ai) from a different network sees the same, so it is
      server-side, not a sandbox/UA/proxy artifact.
    - ``http://patchcoffee.shop/`` → 409 with ``error code: 1001``.
    - ``https://patchcoffee.shop.myshopify.com/`` → same TLS failure;
      other candidate handles (``patchcoffee``/``patch-coffee``) return
      Shopify's "Store unavailable" page.

    Together this indicates a paused or unmapped Shopify store rather than a
    bot block, so no special headers/UA/Playwright handling is warranted yet.
    The scraper is wired to the standard root ``/products.json`` endpoint (no
    curated collection could be discovered while the storefront is down) with
    extended timeouts/retries; it should start working as soon as the store
    comes back online. Currency is pinned to USD (US roaster) to guard against
    Shopify Markets geo-conversion once the store serves again.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Patch Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Patch",
            base_url="https://patchcoffee.shop",
            products_json_urls=["https://patchcoffee.shop/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=3.0,
            max_retries=5,
            timeout=45.0,
            use_optimized_mode=True,
        )

        # Exclude genuine non-coffee items (gift cards, equipment, merch,
        # subscriptions) defensively — the catalogue could not be enumerated
        # while the store is down, so the list is the standard default set.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "sampler",
            "taster-pack",
            "apparel",
            "mug",
            "tumbler",
            "hoodie",
            "tshirt",
        ]

        # Pin the home-market currency (US roaster): the storefront could not
        # be probed to verify via /cart.js while it is down, so make USD
        # authoritative before Shopify Markets geo-detection can override it.
        self.store_currency = "USD"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Patch Coffee product URLs.

        Shopify's canonical product pages are the no-collection form
        ``/products/<handle>``, so strip any ``/collections/<slug>`` segment.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
