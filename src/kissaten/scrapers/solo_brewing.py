"""SOLO Brewing scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)

# The curated our-beans collection misses several beans that exist in the
# store, so fetch collections/all and keep only the coffee product types.
# The untyped "" entries are allowed through and filtered by exclude_slugs
# (the store leaves brew gear and gift cards untyped, while two untyped
# entries — geisha-zeo and the Fermentation Project bundle — are coffee).
_COFFEE_PRODUCT_TYPES = {"Specialty Coffee Beans", "Coffee Kit", "Drip Coffee", "Cascara", ""}


@register_scraper(
    name="solo-brewing",
    display_name="Solo Brewing",
    roaster_name="Solo Brewing",
    website="https://solobrewing.pt",
    description="Portuguese specialty coffee roaster in Porto offering single "
    "origins and experimental ferment lots, including the James Hoffmann / "
    "Lucia Solis Fermentation Project kit.",
    requires_api_key=True,
    currency="EUR",
    country="Portugal",
    status="experimental",
)
class SoloBrewingScraper(ShopifyJsonScraper):
    """Scraper for SOLO Brewing (solobrewing.pt) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize SOLO Brewing scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Solo Brewing",
            base_url="https://solobrewing.pt",
            products_json_urls=["https://solobrewing.pt/collections/all/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # collections/all is filtered on the coffee product types above; the
        # exclude list removes the untyped brew gear and gift card. The
        # Fermentation Project kit and bundle are kept and flagged downstream.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "coaster",
            "cleaner",
            "kalita",
            "sibarist",
            "server-solo",
            "aeropress",
            "filter",
            "brewer",
            "dripper",
        ]

        # Pin the home-market currency: Shopify Markets may serve
        # geo-converted prices to datacenter IPs, and the base-class
        # display-name currency lookup falls back to GBP. The home
        # currency was verified against /cart.js, so make it authoritative.
        self.store_currency = "EUR"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs, keeping only coffee product types.

        ``collections/all`` mixes beans with brew gear, subscriptions and a
        gift card (some of them untyped in Shopify), so keep only the coffee
        product types plus untyped entries, then apply the slug exclusions.
        """
        products = await self._fetch_all_shopify_products(store_url)
        found_urls = []

        for product in products:
            handle = product.get("handle")
            if not handle:
                continue

            # Only accept coffee product types (untyped entries pass and are
            # filtered by the slug exclusions below).
            if product.get("product_type", "") not in _COFFEE_PRODUCT_TYPES:
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

        return found_urls

    def preprocess_product_url(self, url: str) -> str:
        """Standardize SOLO Brewing product URLs.

        solobrewing.pt's canonical product pages are the no-collection form
        ``/products/<handle>``, so strip the ``/collections/<slug>`` segment.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
