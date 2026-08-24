"""Allpress (UK) scraper implementation with Shopify JSON extraction.

Allpress Espresso's UK storefront is Shopify-hosted. ``uk.shop.allpressespresso.com``
redirects to the canonical ``uk.allpress.com`` host; the curated ``coffee``
collection contains each blend/single origin once as a *retail* product and
again as wholesale duplicates (``-office`` and ``-3kg-whole-beans`` /
``-3kg-office`` suffixes), plus a ``discovery-coffee-subscription`` product.

The retail products' URLs are deduplicated by dropping the ``-office`` /
``-3kg`` wholesale variants and the subscription (a genuine service). No
tasting-kit/sampler tokens are excluded (none exist in this collection; the
base ``_apply_product_flags`` handles any future kits).

The product JSON body_html is short and the rendered product pages add nothing
better than the injected JSON context (the page's "Roaster's Notes" / "Bean
Origins" accordions are empty), so the scraper runs JSON-only
(``scrape_product_pages=False``, ``use_optimized_mode=True``).
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="allpress",
    display_name="Allpress",
    roaster_name="Allpress Coffee Roasters",
    website="https://uk.shop.allpressespresso.com",
    description=(
        "London-based specialty espresso roaster; the UK shop sells the classic "
        "Allpress espresso blends and rotating single-origin coffees."
    ),
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class AllpressScraper(ShopifyJsonScraper):
    """Scraper for Allpress UK (uk.allpress.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Allpress (UK) scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Allpress Coffee Roasters",
            base_url="https://uk.allpress.com",
            # Curated Coffee collection on the canonical (redirect target) host:
            # uk.shop.allpressespresso.com serves the same data but its product
            # pages redirect to uk.allpress.com, so build URLs on the canonical
            # host to keep the history keyed to the real pages.
            products_json_urls=["https://uk.allpress.com/collections/coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The rendered page adds nothing over the JSON context; run JSON-only.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Genuine services only — the coffee collection carries a discovery
        # subscription product. No tasting-kit tokens are excluded.
        self.exclude_slugs = [
            "subscription",
            "capsule",
            "gift-card",
            "gift",
            "equipment",
            "merchandise",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Strip collection segments; Allpress product pages are
        ``/products/<handle>`` (no collection prefix)."""
        return f"{self.base_url}/products/{url.rstrip('/').split('/products/')[-1].split('?')[0]}"

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs, keeping only the retail coffee variants.

        The curated Coffee collection repeats each coffee as a retail product
        and as wholesale variants. Retail is identified by the absence of the
        ``-office`` / ``-3kg`` suffixes (NOT kit tokens — wholesale duplicates,
        safe to drop); the ``discovery-…-subscription`` product is a genuine
        service and is dropped via ``exclude_slugs``.
        """
        products = await self._fetch_all_shopify_products(store_url)
        found_urls = []

        for product in products:
            handle = product.get("handle")
            if not handle:
                continue

            title = product.get("title", "") or ""

            # Drop wholesale duplicates and genuine services. ``-office`` and
            # ``-3kg`` are wholesale purchase-form variants of the same coffee
            # (NOT tasting-kit tokens), so it's safe to exclude them.
            if "-office" in handle or "-3kg" in handle:
                logger.debug(f"Skipping wholesale variant of retail coffee: {handle}")
                continue

            # Skip explicitly excluded service slugs.
            if any(slug in handle for slug in self.exclude_slugs):
                logger.debug(f"Skipping excluded product slug: {handle}")
                continue

            # Build the product URL off the collection base, then canonicalize.
            base_path = store_url.replace("/products.json", "")
            url = self.preprocess_product_url(f"{base_path}/products/{handle}")

            # Store metadata + stock keyed by the formatted URL.
            self._shopify_product_data[url] = product
            is_available = any(v.get("available", False) for v in product.get("variants", []))
            self._shopify_stock_status[url] = is_available

            if self.is_coffee_product_url(url) and self.is_coffee_product_name(title):
                found_urls.append(url)

        # Dedup on the canonical/formatted URLs (a handle can only appear once
        # per collection, but the canonicalization above may collapse forms).
        return self.deduplicate_urls(found_urls)
