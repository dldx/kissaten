"""Moongoat scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)

# curl_cffi requests from a datacenter IP are geo/market-detected by Shopify
# Markets and served converted prices (EUR was observed for a EU IP). Passing
# country=US pins Moongoat's home market so products.json always reports USD
# prices.
_MARKET_PARAM = "country=US"


@register_scraper(
    name="moongoat",
    display_name="Moongoat",
    roaster_name="Moongoat",
    website="https://moongoat.com",
    description="US specialty coffee roaster in Fredericksburg, Virginia, roasting "
    "single origins and signature blends, home of the James Hoffmann Fermentation Project set.",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class MoongoatScraper(ShopifyJsonScraper):
    """Scraper for Moongoat (moongoat.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Moongoat scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Moongoat",
            base_url="https://moongoat.com",
            products_json_urls=["https://moongoat.com/collections/all/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=1.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Home market is pinned via country=US (see _fetch_all_shopify_products).
        # Force the currency to USD and mark it as detected so the
        # collection-page detection path in _scrape_new_products (which could
        # see a geo-converted currency) is skipped.
        self.store_currency = "USD"
        self._currency_detected = True

        # There is no curated coffee collection: collections/all mixes matcha,
        # tea, botanicals, merch and gear, which the product_type/tag filter in
        # _extract_product_urls_from_store removes. These handles are Shopify
        # -classified "Coffee" but are not beans (roasted tea, ready-to-drink).
        self.exclude_slugs = [
            "hojicha",
            "rotating-cold-brew",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def _fetch_all_shopify_products(self, products_json_url: str) -> list[dict]:
        """Fetch all products from the products.json endpoint with the US market pinned.

        Mirrors ``ShopifyJsonScraper._fetch_all_shopify_products`` but appends
        ``country=US`` to each paginated request. Without it, Shopify Markets
        geo-detects the datacenter IP and serves converted prices (EUR was
        observed) instead of Moongoat's home USD prices.
        """
        all_products = []
        page = 1
        limit = 250

        while True:
            url = f"{products_json_url}?{_MARKET_PARAM}&limit={limit}&page={page}"
            logger.info(f"Fetching Shopify products: {url}")

            data, use_playwright = await self._fetch_page_with_escalation(url)
            if data is None:
                if products_json_url not in self._failed_listing_urls:
                    self._failed_listing_urls.append(products_json_url)
                break

            products = data.get("products", [])
            if not products:
                break

            all_products.extend(products)
            logger.debug(f"Fetched {len(products)} products from page {page}")

            if len(products) < limit:
                break

            page += 1
            if use_playwright:
                logger.debug(f"Page {page - 1} escalated to Playwright; re-attempting httpx on page {page}.")

        return all_products

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs, keeping only coffee beans plus the Fermentation Project set.

        ``collections/all`` mixes many non-coffee categories (matcha, tea,
        botanicals, merch, gear) that mostly carry an empty ``product_type``.
        Keep only products Shopify itself classifies as ``Coffee``, plus the
        James Hoffmann Fermentation Project set which is identified by its
        ``fermentationproject`` tag but has an empty product type.
        """
        products = await self._fetch_all_shopify_products(store_url)
        found_urls = []

        for product in products:
            handle = product.get("handle")
            if not handle:
                continue

            product_type = (product.get("product_type") or "").strip()
            tags = product.get("tags") or []
            if product_type != "Coffee" and "fermentationproject" not in tags:
                logger.debug(f"Skipping non-coffee product: {handle} ({product_type})")
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

    def preprocess_product_url(self, url: str) -> str:
        """Strip the collection segment to match Moongoat's canonical product URLs.

        ShopifyJsonScraper builds product URLs as
        ``<products.json base>/products/<handle>``, which yields a
        ``/collections/all/products/<handle>`` form. Moongoat's canonical
        product pages are served at ``/products/<handle>``.
        """
        return re.sub(r"/collections/[^/]+/products/", "/products/", url)
