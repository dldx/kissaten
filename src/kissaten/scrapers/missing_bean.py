"""Missing Bean scraper implementation with Shopify JSON extraction.

Missing Bean (themissingbean.co.uk) is an Oxford-based specialty coffee
roaster. The store is Shopify-hosted; the curated ``coffee`` ("Coffee Beans")
collection is the site's canonical coffee page.

Research notes (2026-08):
- ``collections/coffee/products.json`` (the "Coffee Beans" collection) actually
  returns 17 Coffee-type products plus one Gift Voucher (``gift-subscription``),
  even though ``collections.json`` advertises 118 products for it — the count
  is stale/inflated and must not be trusted. Because a genuine curated coffee
  collection exists, we prefer ``collections/coffee/products.json`` over
  ``products.json`` (which mixes beans with Home Brewing / Merchandise / Gift
  Voucher), and filter on ``product_type == "Coffee"`` inside it to drop the
  lone gift-voucher entry.
- Canonical product pages are the no-collection form ``/products/<handle>``
  (the collection URL 200s, but the site serves the bare handle form), so we
  strip the ``/collections/coffee`` segment that the products.json base URL
  injects.
- Currency is GBP (the store serves ``£`` prices and sets ``cart_currency=GBP``).
  We pin ``store_currency`` so the geo-detected market can't override it.
- Scrape shape: JSON-only (``scrape_product_pages=False``). The Shopify
  ``body_html`` already carries the structured bean detail (Tasting Notes,
  Best Enjoyed As / roast profile, Process & Varietal, Elevation, farm flags)
  and the page's only extra content is a marketing narrative paragraph (a
  separate site section, not present in the product JSON) that adds no
  CoffeeBean fields. No accordion/carousel/tab-hidden content exists on the
  product page, so no carousel guard is triggered.

Sampler / taster / discovery products (e.g. ``multi-coffee-tasting-box``) are
deliberately NOT excluded — they flow through to be flagged as tasting kits by
``_apply_product_flags``. Only genuine non-bean items (subscriptions, gift
cards, equipment, merch) are excluded.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="missing-bean",
    display_name="Missing Bean",
    roaster_name="Missing Bean",
    website="https://www.themissingbean.co.uk",
    description="Oxford-based specialty coffee roaster known for "
    "genuine whole-bean coffees, single origins and signature blends",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class MissingBeanScraper(ShopifyJsonScraper):
    """Scraper for Missing Bean (themissingbean.co.uk) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Missing Bean scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Missing Bean",
            base_url="https://www.themissingbean.co.uk",
            products_json_urls=[
                "https://www.themissingbean.co.uk/collections/coffee/products.json",
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

        # Exclude non-bean products (subscriptions, gift cards, equipment,
        # merch). Sampler/taster/discovery products (e.g. multi-coffee-tasting
        # box) are intentionally NOT excluded here — they flow through to be
        # flagged as tasting kits via _apply_product_flags.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift-voucher",
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
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def _get_tasting_kit_url_patterns(self) -> list[str]:
        """Add Missing Bean's Multi-Coffee Tasting Box to the kit patterns.

        The base patterns match ``tasting-kit`` / ``tasting-set`` but not the
        handle form ``multi-coffee-tasting-box``, so without this override the
        no-origin sampler would be dropped by ``_extract_bean_with_ai`` instead
        of flowing through to be flagged ``is_tasting_kit`` /
        ``requires_review`` for the admin review queue.
        """
        return super()._get_tasting_kit_url_patterns() + ["tasting-box"]

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Missing Bean product URLs.

        The canonical/live product pages are the no-collection form
        ``/products/<handle>``, so strip the ``/collections/coffee`` segment
        that the products.json base URL injects.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs, keeping only whole-bean coffee.

        The default base-class filter (``is_coffee_product_url`` +
        ``is_coffee_product_name``) is intentionally conservative and would pass
        the collection's non-bean Gift product. Since the curated ``coffee``
        collection mixes beans with a couple of non-bean items, filter
        explicitly on the Shopify ``product_type == "Coffee"`` before building
        the URL.
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
