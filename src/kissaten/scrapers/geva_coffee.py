"""Geva Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="geva-coffee",
    display_name="Geva Coffee",
    roaster_name="Geva Coffee",
    website="https://www.gevacoffee.com",
    description="Houston, Texas specialty roaster and café operator offering single-origin "
    "coffees, blends and the James Hoffmann Fermentation Project kit",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class GevaCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Geva Coffee (gevacoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Geva Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Geva Coffee",
            base_url="https://www.gevacoffee.com",
            products_json_urls=["https://www.gevacoffee.com/collections/all/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Ready-to-drink cold brew products are beverages, not beans.
        self.exclude_slugs = [
            "cold-brew",
            "cubano-cold",
        ]

        # Pin the home-market currency: Shopify Markets may serve
        # geo-converted prices to datacenter IPs, and the base-class
        # display-name currency lookup falls back to GBP. The home
        # currency was verified against /cart.js, so make it authoritative.
        self.store_currency = "USD"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Geva Coffee product URLs.

        Geva's canonical product pages are the no-collection form
        ``/products/<handle>``, so strip the ``/collections/<slug>`` segment.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs, keeping only Shopify-classified coffee.

        ``collections/all`` mixes coffee with syrups, teas, espresso machines,
        grinders, milks and merch, so filter explicitly on the Shopify
        ``product_type == "Coffee"`` before building the URL (same pattern as
        the Intelligentsia scraper). The (Pre-Order) Fermentation Project Kit is
        ``product_type == "Coffee"`` and is intentionally kept — it is flagged
        as a tasting kit downstream, not excluded.
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
