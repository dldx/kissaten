"""Yellow Bourbon Coffee Roasters scraper implementation with Shopify JSON extraction.

Yellow Bourbon Coffee Roasters (yellowbourbon.net, Northampton) runs a
Shopify storefront. The curated ``shop`` ("Coffee") collection is the site's
canonical coffee page and returns exactly the currently-available whole-bean
coffees (single origins, house blends and the decaf), all classified as
``product_type == "Coffee"``.

Research notes (2026-08):
- ``collections/shop/products.json`` returns 7 Coffee-type products
  (``collections.json`` advertises an inflated count of 51 for it that must not
  be trusted). Because a genuine curated coffee collection exists, we prefer
  ``collections/shop/products.json`` over ``products.json`` (22 mixed products)
  and filter on ``product_type == "Coffee"`` inside it.
- Canonical product pages are the no-collection form ``/products/<handle>``
  (confirmed via the page's ``rel=canonical``), so we strip the
  ``/collections/shop`` segment that the products.json base URL injects.
- Currency is GBP (the store serves ``£`` prices and sets
  ``cart_currency=GBP``). We pin ``store_currency`` so a geo-detected market
  can't override it.
- Scrape shape: JSON-only (``scrape_product_pages=False``). The Shopify
  ``body_html`` carries the structured bean detail (tasting notes, blend
  components) and the variants carry the whole-bean price/weight options.

Sampler / taster / kit products are deliberately NOT excluded — they flow
through to be flagged as tasting kits by ``_apply_product_flags``. Only
genuine non-bean items (subscriptions, gift cards, equipment, merch) are
excluded.
"""

import logging

from . import _curl_http as httpx
from .base import WebBotAuth
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="yellow-bourbon",
    display_name="Yellow Bourbon Coffee Roasters",
    roaster_name="Yellow Bourbon Coffee Roasters",
    website="https://yellowbourbon.net",
    description="Northampton-based specialty coffee roaster offering single "
    "origin coffees, espresso blends and a Swiss Water decaf, sourced and "
    "roasted in small batches",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class YellowBourbonScraper(ShopifyJsonScraper):
    """Scraper for Yellow Bourbon Coffee Roasters (yellowbourbon.net) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Yellow Bourbon Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Yellow Bourbon Coffee Roasters",
            base_url="https://yellowbourbon.net",
            products_json_urls=[
                "https://yellowbourbon.net/collections/shop/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Pin the home currency (GBP) so Shopify Markets geo-conversion can't
        # stamp a datacenter-IP market price onto every bean.
        self.store_currency = "GBP"
        self._currency_detected = True

        # yellowbourbon.net's edge rejects curl_cffi's default libcurl TLS
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

        # Exclude non-bean products (subscriptions, gift cards, equipment,
        # merch). Sampler/taster/kit products are intentionally NOT excluded
        # here — they flow through to be flagged as tasting kits via
        # _apply_product_flags.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
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
            "tote",
            "capsules",
            "pods",
            "cold-brew-cans",
            "easy-pour",
            "drip-bags",
            "grinder",
            "v60",
            "chemex",
            "aeropress",
            "kalita",
            "detergent",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Yellow Bourbon product URLs.

        The canonical/live product pages are the no-collection form
        ``/products/<handle>``, so strip the ``/collections/shop`` segment that
        the products.json base URL injects.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs, keeping only whole-bean coffee.

        The default base-class filter (``is_coffee_product_url`` +
        ``is_coffee_product_name``) is intentionally conservative. Since the
        curated ``shop`` collection is the canonical coffee page, filter
        explicitly on the Shopify ``product_type == "Coffee"`` before building
        the URL to keep only whole-bean coffees.
        """
        products = await self._fetch_all_shopify_products(store_url)
        found_urls = []

        for product in products:
            handle = product.get("handle")
            if not handle:
                continue

            # Only accept products Shopify itself classifies as coffee.
            if product.get("product_type", "") != "Coffee":
                logger.debug(f"Skipping non-coffee product type: {handle} ({product.get('product_type')})")
                continue

            # Skip explicitly excluded product slugs (matches if slug is a substring of handle).
            if any(slug in handle for slug in self.exclude_slugs):
                logger.debug(f"Skipping excluded product slug: {handle}")
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
