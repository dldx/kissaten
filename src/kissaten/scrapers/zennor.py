"""Zennor Coffee scraper implementation with Shopify JSON extraction.

Zennor Coffee (zennorcoffee.co.uk) is a Glasgow-based specialty coffee roaster
(roastery in Dennistoun, café in the Southside) roasting small-batch single
origins and house blends.

The site is Shopify-hosted. There is no single curated "all coffee" collection
that contains every bean: the ``coffee`` (Core Collection), ``rare`` (Rare &
Limited) and ``seasonal-lots`` (Seasonal Micro Lots) collections together cover
the currently-live beans but miss the sold-out product (Finca Anaya), which only
appears in ``/collections/all``. We therefore read ``/collections/all`` and
filter on Shopify's ``product_type == "Coffee"`` — this yields exactly the 12
whole-bean coffees (11 purchasable + 1 sold out) and drops the equipment /
accessories (filters, brewers, the cupping spoon) that share the collection.

Product URLs are canonicalised to the no-collection form the live site serves
(``/products/<handle>``). Extraction is JSON-only: the Shopify JSON carries the
product name, variants, prices and body_html, so no product page is fetched.
"""

import logging

from . import _curl_http as httpx
from .base import WebBotAuth
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="zennor",
    display_name="Zennor Coffee",
    roaster_name="Zennor Coffee",
    website="https://zennorcoffee.co.uk",
    description="Glasgow-based specialty coffee roaster (roastery in Dennistoun, "
    "café in the Southside) roasting small-batch single-origin coffees and "
    "house blends.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class ZennorCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Zennor Coffee (zennorcoffee.co.uk) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Zennor Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Zennor Coffee",
            base_url="https://zennorcoffee.co.uk",
            products_json_urls=[
                "https://zennorcoffee.co.uk/collections/all/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The store's home market is the UK (GBP). Pin it so Shopify Markets
        # geolocation can never stamp USD-converted prices onto the beans.
        self.store_currency = "GBP"
        self._currency_detected = True

        # zennorcoffee.co.uk's edge rejects curl_cffi's default libcurl TLS
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

        # Defensive net on top of the product_type == "Coffee" filter. Genuine
        # equipment/accessories live under empty product_type and are already
        # excluded, but these tokens guard against any reclassified products.
        # Sampler / taster / kit tokens are intentionally NOT included so curated
        # tasting kits land in the admin review queue rather than being dropped.
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
            "tee",
            "capsules",
            "pods",
            "grinder",
            "dripper",
            "filter",
            "spoon",
            "kettle",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Zennor Coffee product URLs.

        The live site serves products at the no-collection form
        ``/products/<handle>`` (confirmed via the pages' ``rel=canonical``), so
        strip the ``/collections/<slug>`` segment that the products.json base
        URL injects.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs, keeping only whole-bean coffee.

        The default base-class filter (``is_coffee_product_url`` +
        ``is_coffee_product_name``) is intentionally conservative and would pass
        the collection's equipment items (filters, brewers, cupping spoon),
        since their handles don't reliably trip an exclude keyword. Filter
        explicitly on the Shopify ``product_type == "Coffee"`` before building
        the URL so only beans are kept.
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
