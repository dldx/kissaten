"""19grams scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)

# 19grams labels its beans with several product_type values; everything else
# in /collections/all is equipment, training/cupping events, merch or gift cards.
COFFEE_PRODUCT_TYPES = {
    "Coffee",
    "Kaffee",
    "Filter",
    "Espresso",
    "Collaboration Coffee",
    "Tres Cabezas",
}


@register_scraper(
    name="19-grams",
    display_name="19grams",
    roaster_name="19grams",
    website="https://19grams.coffee",
    description="Berlin-based specialty coffee roaster offering a wide range of single-origin "
    "filter and espresso roasts, collaborations, and the James Hoffmann Fermentation Project kit",
    requires_api_key=True,
    currency="EUR",
    country="Germany",
    status="experimental",
)
class NineteenGramsScraper(ShopifyJsonScraper):
    """Scraper for 19grams (19grams.coffee) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize 19grams scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="19grams",
            base_url="https://19grams.coffee",
            products_json_urls=["https://19grams.coffee/collections/all/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Pin the home-market currency: Shopify Markets can serve geo-converted
        # prices depending on caller IP / Accept-Language, so runtime detection
        # is not trusted.
        self.store_currency = "EUR"
        self._currency_detected = True

        # Coffee products are selected by product_type (see
        # _extract_product_urls_from_store); these slug exclusions remove the
        # subscription/test-run/gift-box leftovers that carry a coffee-ish
        # product_type.
        self.exclude_slugs = [
            "abo",  # subscriptions
            "club",  # coffee-club gift subscriptions
            "kapseln",  # pods/capsules
            # NOTE: coffee gift bundles (geschenkbox-*, kaffee-set-*, probierset-*,
            # test-box-*) are deliberately NOT excluded — they are coffee for sale
            # and get is_tasting_kit/requires_review flagging downstream.
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def _canonicalize_url(self, url: str) -> str:
        # Canonical product pages are /products/<handle> (collection-prefixed
        # URLs 301-redirect there); collapse the collection segment so history
        # entries match the canonical form.
        return re.sub(r"/collections/[^/]+/products/", "/products/", url)

    def preprocess_product_url(self, url: str) -> str:
        """Canonicalize collection-prefixed product URLs to ``/products/<handle>``."""
        return self._canonicalize_url(url)

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs, keeping only products Shopify classifies as coffee.

        19grams has no curated all-coffee collection and ``collections/all``
        mixes beans with equipment, training/cupping events, merchandise and
        gift cards across many different product_type values, so filter on an
        explicit whitelist of coffee product types before applying the
        base-class URL/name filters.
        """
        products = await self._fetch_all_shopify_products(store_url)
        found_urls = []

        for product in products:
            handle = product.get("handle")
            if not handle:
                continue

            # Only accept products Shopify classifies as one of the coffee types.
            if product.get("product_type", "") not in COFFEE_PRODUCT_TYPES:
                logger.debug(f"Skipping non-coffee product type: {handle} ({product.get('product_type')})")
                continue

            # Skip explicitly excluded product slugs (matches if slug is a substring of handle).
            if any(slug in handle for slug in self.exclude_slugs):
                logger.debug(f"Skipping excluded product slug: {handle}")
                continue

            # Build product URL using the base of the products.json URL.
            base_path = store_url.replace("/products.json", "")
            url = f"{base_path}/products/{handle}"

            # Canonicalize to the site's real /products/<handle> form.
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
