"""The Blending Room scraper implementation with Shopify JSON extraction.

The Blending Room (www.theblendingroom.co.uk) is an independent coffee
roaster based in Hull, East Yorkshire, roasting since 2009 at 30 Unit Factory
Estate, Boulevard, Hull HU3 4AY. Its curated ``/collections/coffee`` Shopify
collection carries exactly the whole-bean catalogue — every product is
Shopify-labelled ``product_type == "Coffee"`` — so a strict ``product_type``
include-filter reproduces the curated set without any hardcoded bean names.

The catalogue includes two curated variety-pack samplers
(``single-origin-variety-pack``, ``core-coffee-variety-pack``). These are
samplers, NOT exclusions: they flow through to ``_apply_product_flags``, and
because their handles carry no standard kit token, ``postprocess_review_flags``
forces ``is_tasting_kit`` on them so they land in the admin review queue
(``requires_review``) instead of being silently dropped or shown to the public.

The site prices in GBP (``Shopify.currency = {"active":"GBP"}`` on every page)
and serves its canonical product pages at ``/products/<handle>`` (no collection
segment, confirmed via ``rel=canonical``), so the collection segment produced
by the products.json base is stripped in ``preprocess_product_url``.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="the-blending-room",
    display_name="The Blending Room",
    roaster_name="The Blending Room",
    website="https://www.theblendingroom.co.uk",
    description="Independent coffee roaster in Hull, East Yorkshire, roasting "
    "since 2009 at 30 Unit Factory Estate, Boulevard, Hull HU3 4AY, with a "
    "curated range of single-origin and blend coffees priced in GBP.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class TheBlendingRoomScraper(ShopifyJsonScraper):
    """Scraper for The Blending Room (theblendingroom.co.uk) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize The Blending Room scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="The Blending Room",
            base_url="https://www.theblendingroom.co.uk",
            products_json_urls=[
                "https://www.theblendingroom.co.uk/collections/coffee/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The store always prices in GBP. Pin the currency so a geolocated
        # datacenter caller can never have converted prices stamped on beans.
        self.store_currency = "GBP"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Strip the collection segment so URLs match the site's canonical form.

        ShopifyJsonScraper builds collection-prefixed URLs (e.g.
        ``/collections/coffee/products/<handle>``) from the products.json base,
        but the site serves its canonical product pages at
        ``/products/<handle>``. Collapse to that form.
        """
        if "/collections/" in url and "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs, keeping only whole-bean coffee.

        The curated ``/collections/coffee`` collection carries the whole-bean
        catalogue. A strict Shopify ``product_type == "Coffee"`` include-filter
        keeps the set stable and lets the two curated variety-pack samplers
        flow through to ``_apply_product_flags`` (which flags them for admin
        review) rather than silently dropping them.
        """
        products = await self._fetch_all_shopify_products(store_url)
        found_urls = []

        for product in products:
            handle = product.get("handle")
            if not handle:
                continue

            # Only accept whole-bean coffee, using the site's own classification.
            if (product.get("product_type") or "").strip().lower() != "coffee":
                logger.debug(f"Skipping non-bean product type: {handle} ({product.get('product_type')})")
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

    def postprocess_review_flags(self, bean, url: str):
        """Force ``is_tasting_kit`` on the curated variety-pack samplers.

        The two variety packs (``single-origin-variety-pack``,
        ``core-coffee-variety-pack``) are curated samplers of several coffees,
        but their handles and names carry no standard kit token
        (sampler/taster/sample-pack/...), so the base flagger cannot detect
        them. Their URLs identify them as curated variety packs, so force
        ``is_tasting_kit`` here — ``_apply_product_flags`` then raises
        ``requires_review`` and they land in the admin review queue.
        """
        if bean is not None and url and "variety-pack" in str(url).lower():
            bean.is_tasting_kit = True
        return bean
