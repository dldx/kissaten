"""Intelligentsia Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="intelligentsia",
    display_name="Intelligentsia",
    roaster_name="Intelligentsia",
    website="https://www.intelligentsia.com",
    description="Legendary Chicago-based specialty coffee roaster known as one of the "
    "pioneers of the third wave coffee movement, with a vast catalog of single origin "
    "coffees and signature espresso blends",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="available",
)
class IntelligentsiaCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Intelligentsia (intelligentsia.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Intelligentsia Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Intelligentsia",
            base_url="https://www.intelligentsia.com",
            products_json_urls=[
                "https://www.intelligentsia.com/collections/all-coffee/products.json"
            ],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Exclude non-drip non-espresso Coffee-type products (instant, cold, bundles,
        # subscriptions) while keeping every whole-bean coffee in the catalog.
        self.exclude_slugs = [
            "subscription",
            "instant",
            "cold-coffee",
            "bundle",
            "variety-bundle",
            "gift-card",
            "gift",
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
            "capsules",
            "pods",
            "cold-brew-cans",
            "easy-pour",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Intelligentsia product URLs.

        Intelligentsia's canonical/live product pages are the no-collection form
        ``/products/<handle>``, so strip the ``/collections/<slug>`` segment that the
        products.json base URL injects.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs, keeping only whole-bean coffee.

        The default base-class filter (``is_coffee_product_url`` +
        ``is_coffee_product_name``) is intentionally conservative and will pass
        drinkware/equipment/gift items that don't trip an exclude keyword. Since
        ``collections/all`` mixes many non-coffee categories, filter explicitly on
        the Shopify ``product_type == "Coffee"`` before building the URL.
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
