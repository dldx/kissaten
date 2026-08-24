"""Acorn Coffee scraper implementation with Shopify JSON extraction.

Acorn Coffee (acornscoffee.com) is a Shopify store in Hampshire, UK. The
``products.json`` catalog mixes ~19 coffee products (``product_type``
``"Coffee"``) with gift-box bundles and a hot-chocolate powder that carry an
empty ``product_type``. The include-filter keeps only ``product_type == Coffee``
while the explicitly-not-coffee handles (gift bundles + hot-chocolate) are
dropped. No tasting-kit/sampler tokens are excluded — the base
``_apply_product_flags`` flags any kit it finds for admin review.

Coffee body_html carries full origin/tasting-note copy, so the scraper runs
JSON-only (``scrape_product_pages=False``, ``use_optimized_mode=True``) on the
injected Shopify context.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="acorn",
    display_name="Acorn Coffee",
    roaster_name="Acorn Coffee",
    website="https://acornscoffee.com",
    description=(
        "Small-batch coffee roaster based in Bordon, Hampshire, roasting "
        "single origins and house blends."
    ),
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class AcornScraper(ShopifyJsonScraper):
    """Scraper for Acorn Coffee (acornscoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Acorn Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Acorn Coffee",
            base_url="https://acornscoffee.com",
            products_json_urls=["https://acornscoffee.com/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The coffee bodies carry full origin/tasting info; run JSON-only.
        self.store_currency = "GBP"
        self._currency_detected = True

        # The 5 non-coffee handles in the products.json feed. The gift-bundle
        # boxes (smooth-everyday, fruity-flavours, intense-experience,
        # chocolatey-collection) and hot-chocolate-powder carry empty
        # product_type. None of these are tasting-kit/sampler tokens and the
        # coffee filter below drops them regardless; the set is defensive.
        self._non_coffee_handles = {
            "smooth-everyday",
            "fruity-flavours",
            "intense-experience",
            "chocolatey-collection",
            "hot-chocolate-powder",
        }

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Acorn URLs by removing collection segments.

        Acorn's live product pages are the no-collection form
        ``/products/<handle>``.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs, keeping only whole-bean coffee.

        The curated products pool mixes coffee with gift bundles and a
        hot-chocolate powder, so filter explicitly: keep a product when the
        Shopify ``product_type`` is "Coffee" and the handle is not one of the
        known non-coffee products.
        """
        products = await self._fetch_all_shopify_products(store_url)
        found_urls = []

        for product in products:
            handle = product.get("handle")
            if not handle:
                continue

            title = product.get("title", "") or ""
            product_type = (product.get("product_type") or "").strip().lower()

            # Coffee include-filter: Shopify product_type "Coffee" and not a
            # known non-coffee product. No kit tokens are excluded.
            is_coffee_type = product_type == "coffee"
            if not is_coffee_type or handle in self._non_coffee_handles:
                logger.debug(f"Skipping non-coffee product: {handle} ({title!r})")
                continue

            # Build product URL using the base of the products.json URL.
            base_path = store_url.replace("/products.json", "")
            url = f"{base_path}/products/{handle}"

            # Preprocess the URL (e.g. to remove collection segments).
            url = self.preprocess_product_url(url)

            # Store metadata for later enrichment and stock status (keyed by
            # the same formatted URL used for extraction / stock updates).
            self._shopify_product_data[url] = product
            is_available = any(v.get("available", False) for v in product.get("variants", []))
            self._shopify_stock_status[url] = is_available

            # Final conservative gate (everything above already selected coffee).
            if self.is_coffee_product_url(url) and self.is_coffee_product_name(title):
                found_urls.append(url)

        # Dedup on the canonical/formatted URLs.
        return self.deduplicate_urls(found_urls)
