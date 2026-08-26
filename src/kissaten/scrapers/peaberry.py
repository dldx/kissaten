"""Peaberry Coffee Roasters scraper implementation with Shopify JSON extraction.

Peaberry Coffee Roasters (peaberrycoffee.co.uk) is a family roastery in
Andover, Hampshire (UK) roasting a curated catalogue of ~15 whole-bean coffees
(single origins, blends, and decaf). Their curated
``/collections/all-coffees`` Shopify collection carries the whole-bean set
alongside grinders, gift sets/hampers, tins, tote bags, and other non-bean
merchandise, so this scraper reproduces the curated set with a token-based
exclusion that drops equipment/gifts while letting any tasting-kit sampler
flow through to ``_apply_product_flags`` (which flags it for admin review)
instead of being silently dropped.

The site prices in GBP (``Shopify.currency = {"active":"GBP","rate":"1.0"}``
and ``og:price:currency = "GBP"`` on every product page) and serves its
canonical product pages at ``/products/<handle>`` (no collection segment), so
the store currency is pinned and collection segments are stripped.
"""

import logging

from . import _curl_http as httpx
from .base import WebBotAuth
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="peaberry",
    display_name="Peaberry Coffee Roasters",
    roaster_name="Peaberry Coffee Roasters",
    website="https://peaberrycoffee.co.uk",
    description="Family roastery in Andover, Hampshire, roasting single-origin, "
    "blend, and decaf whole-bean coffees.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class PeaberryCoffeeRoastersScraper(ShopifyJsonScraper):
    """Scraper for Peaberry Coffee Roasters (peaberrycoffee.co.uk) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize the Peaberry Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Peaberry Coffee Roasters",
            base_url="https://peaberrycoffee.co.uk",
            products_json_urls=["https://peaberrycoffee.co.uk/collections/all-coffees/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The site always prices in GBP. Pin the store currency so a geolocated
        # datacenter caller can never have converted prices stamped on beans.
        self.store_currency = "GBP"
        self._currency_detected = True

        # peaberrycoffee.co.uk is a Shopify storefront on the same platform as
        # chippcoffee.co.uk / twodaycoffee.co.uk, whose edges reject curl_cffi's
        # default libcurl TLS fingerprint (403 on products.json) while the
        # "chrome" impersonation profile negotiates successfully. Rebuild the
        # client with that profile, preserving headers/auth/proxy (mirrors
        # chipp.py / twoday.py).
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
        """Strip the collection segment so URLs match the site's canonical form.

        ShopifyJsonScraper builds collection-prefixed URLs (e.g.
        ``/collections/all-coffees/products/<handle>``) from the products.json
        base, but Peaberry serves its canonical product pages at
        ``/products/<handle>``. Collapse to that form.
        """
        if "/collections/" in url and "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url

    def _is_non_bean_product(self, product: dict) -> bool:
        """Return True if a Shopify product is not whole-bean coffee.

        Excludes grinders, gift sets/hampers, tins, tote bags, and other
        equipment/merch, but returns False (kept) for tasting-kit/sampler
        products so they are extracted and flagged ``is_tasting_kit`` /
        ``requires_review`` by ``_apply_product_flags`` rather than being
        dropped. No hardcoded bean names: classification is purely token-based
        on handle/title/product_type (hyphens/underscores normalized to spaces).
        """
        handle = product.get("handle") or ""
        title = (product.get("title") or "").lower()
        product_type = (product.get("product_type") or "").lower()
        combined = f"{handle} {title} {product_type}".replace("-", " ").replace("_", " ")

        # Tasting-kit samplers are retained (flagged for review later), never dropped.
        if self.is_tasting_kit_url(handle):
            return False
        kit_tokens = ("taster", "sampler", "sample pack", "sample box", "tasting", "gift box", "coffee kit")
        if any(token in combined for token in kit_tokens):
            return False

        # Non-bean catalogue: grinders, gifts/hampers, tins, tote bags, and
        # other equipment/merch (e.g. the Rocket Espresso Apartamento machine).
        if any(
            token in combined
            for token in (
                "grinder",
                "apartamento",
                "gift card",
                "gift set",
                "hamper",
                "mug",
                "tote",
                " tin",  # " tin " / "tins" catches branded canisters, not "faustino"
                "tins",
                "hot chocolate",
                "pod",
                "capsule",
                "subscription",
                "equipment",
                "merch",
                "canister",
                "kettle",
                "tumbler",
            )
        ):
            return True
        return False

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs, keeping only whole-bean coffee (and flagged samplers).

        The curated ``/collections/all-coffees`` collection carries the
        whole-bean catalogue. A token-based exclusion (see
        ``_is_non_bean_product``) keeps the set stable while letting
        tasting-kit samplers flow through to ``_apply_product_flags`` for admin
        review rather than dropping them.
        """
        products = await self._fetch_all_shopify_products(store_url)
        found_urls = []

        for product in products:
            handle = product.get("handle")
            if not handle:
                continue

            # Skip explicitly excluded product slugs.
            if any(slug in handle for slug in self.exclude_slugs):
                logger.debug(f"Skipping excluded product slug: {handle}")
                continue

            # Skip non-bean catalogue (grinders, gifts, equipment, merch).
            if self._is_non_bean_product(product):
                logger.debug(f"Skipping non-bean product: {handle} ({product.get('title')})")
                continue

            # Build product URL using the base of the products.json URL.
            base_path = store_url.replace("/products.json", "")
            url = f"{base_path}/products/{handle}"

            # Preprocess the URL (e.g. to remove collection segments).
            url = self.preprocess_product_url(url)

            # Store metadata for later enrichment and stock status.
            self._shopify_product_data[url] = product

            # A product is in stock if any of its variants are available.
            is_available = any(v.get("available", False) for v in product.get("variants", []))
            self._shopify_stock_status[url] = is_available

            # Filter out non-coffee products using base class logic.
            if self.is_coffee_product_url(url) and self.is_coffee_product_name(product.get("title", "")):
                found_urls.append(url)

        # Dedup on the canonical/formatted URLs (post-preprocess) so the returned
        # list is unique even before the base discover_all_product_urls dedups.
        return self.deduplicate_urls(found_urls)
