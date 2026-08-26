"""Volcano Coffee Works scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="volcano",
    display_name="Volcano Coffee Works",
    roaster_name="Volcano Coffee Works",
    website="https://volcanocoffeeworks.com",
    description="South London speciality coffee roaster producing sustainable, "
    "carbon-neutral coffee beans, espresso blends and single origins",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class VolcanoCoffeeWorksScraper(ShopifyJsonScraper):
    """Scraper for Volcano Coffee Works (volcanocoffeeworks.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Volcano Coffee Works scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Volcano Coffee Works",
            base_url="https://volcanocoffeeworks.com",
            products_json_urls=[
                "https://volcanocoffeeworks.com/collections/buy-volcano-coffee/products.json"
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Curated "COFFEE BEANS & GROUND" collection. Pin the store currency so the
        # geo-detected market (Shopify Markets geolocation) can't override the
        # roaster's home currency of GBP.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Exclude non-bean products that Shopify itself still classes as "Coffee":
        # gift sets, cold brew (cans/concentrate) and barista coffee bags. Whole-bean
        # coffee, grounds and tasting/sampler kits (e.g. "Speciality Coffee Starter
        # Box", "Roaster's Choice") are intentionally NOT excluded.
        self.exclude_slugs = [
            "gift",
            "cold-brew",
            "bag",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Strip the collection segment so URLs match the site's canonical form.

        The products.json base is ``/collections/buy-volcano-coffee``, which the
        base class turns into ``/collections/buy-volcano-coffee/products/<handle>``.
        Volcano's real/canonical product pages are ``/products/<handle>``, so drop
        the collection segment.

        Args:
            url: Original product URL

        Returns:
            Canonical ``/products/<handle>`` URL
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs, keeping only whole-bean coffee.

        The curated ``buy-volcano-coffee`` collection mixes beans with a gift set,
        cold brew items and barista bags (all typed ``Coffee``), plus a couple of
        ``Coffee Equipment & Gifts`` and a ``Coffee Subscription``. Filter first on
        the Shopify ``product_type == "Coffee"`` to drop equipment/gifts/subscription,
        then apply the exclude-slug net for the non-bean coffee items.
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

            # Preprocess the URL to the canonical /products/<handle> form.
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
