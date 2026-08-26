"""Chipp Coffee Co scraper implementation with Shopify JSON extraction.

Chipp Coffee Co (chippcoffee.co.uk) is a Leeds, UK roaster (37 Crossland
Court, Czar Street, Holbeck, Leeds LS11 9PR). Their curated
``/collections/coffee`` Shopify collection carries the whole-bean catalogue
(~14 beans) alongside a couple of home-compostable coffee pods and a
roasters-choice subscription. The collection has no clean
``product_type == "beans"`` marker (beans are labelled variously ``Coffee``
or left blank), so this scraper reproduces the curated set with a
token-based exclusion that drops pods/capsules and subscriptions while
letting any tasting-kit sampler flow through to ``_apply_product_flags``
(which flags it for admin review) instead of being silently dropped.

The site prices in GBP (``Shopify.currency = {"active":"GBP","rate":"1.0"}``
on every page) and serves its canonical product pages at
``/products/<handle>`` (no collection segment), so the store currency is
pinned and collection segments are stripped.
"""

import logging

from . import _curl_http as httpx
from .base import WebBotAuth
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="chipp",
    display_name="Chipp Coffee Co",
    roaster_name="Chipp Coffee Co",
    website="https://chippcoffee.co.uk",
    description="Leeds, UK specialty coffee roaster based at 37 Crossland "
    "Court, Czar Street, Holbeck, Leeds LS11 9PR, sourcing and roasting "
    "distinctive single-origin coffees.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class ChippCoffeeCoScraper(ShopifyJsonScraper):
    """Scraper for Chipp Coffee Co (chippcoffee.co.uk) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize the Chipp Coffee Co scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Chipp Coffee Co",
            base_url="https://chippcoffee.co.uk",
            products_json_urls=["https://chippcoffee.co.uk/collections/coffee/products.json"],
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

        # chippcoffee.co.uk's edge rejects curl_cffi's default libcurl TLS
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

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Strip the collection segment so URLs match the site's canonical form.

        ShopifyJsonScraper builds collection-prefixed URLs (e.g.
        ``/collections/coffee/products/<handle>``) from the products.json base,
        but Chipp serves its canonical product pages at ``/products/<handle>``.
        Collapse to that form.
        """
        if "/collections/" in url and "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url

    def _is_non_bean_product(self, product: dict) -> bool:
        """Return True if a Shopify product is not whole-bean coffee.

        Excludes pods/capsules, subscriptions, and other equipment/merch, but
        returns False (kept) for tasting-kit/sampler products so they are
        extracted and flagged ``is_tasting_kit`` / ``requires_review`` by
        ``_apply_product_flags`` rather than being dropped. No hardcoded bean
        names: classification is purely token-based on handle/title/product_type.
        """
        handle = product.get("handle") or ""
        title = (product.get("title") or "").lower()
        product_type = (product.get("product_type") or "").lower()
        combined = f"{handle} {title} {product_type}"

        # Tasting-kit samplers are retained (flagged for review later), never dropped.
        if self.is_tasting_kit_url(handle):
            return False
        kit_tokens = ("taster", "sampler", "sample pack", "sample box", "tasting", "gift box", "coffee kit")
        if any(token in title for token in kit_tokens):
            return False

        # Non-bean catalogue: pods/capsules, subscriptions, equipment/merch.
        if any(token in combined for token in ("pod", "capsule", "subscription", "grinder", "equipment")):
            return True
        if any(token in combined for token in ("gift card", "merch", "mug", "tumbler")):
            return True
        return False

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs, keeping only whole-bean coffee (and flagged samplers).

        The curated ``/collections/coffee`` collection carries the whole-bean
        catalogue. A token-based exclusion (see ``_is_non_bean_product``) keeps
        the set stable while letting tasting-kit samplers flow through to
        ``_apply_product_flags`` for admin review rather than dropping them.
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

            # Skip non-bean catalogue (pods, subscriptions, equipment, merch).
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
