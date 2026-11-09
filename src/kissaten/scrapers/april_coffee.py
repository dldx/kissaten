"""April Coffee scraper implementation.

April moved off a classic Shopify theme to a custom Next.js storefront
(Shopify Storefront API behind the scenes): every
``/collections/<handle>/products.json`` URL now returns a 404 HTML page.
Product data is instead served by the storefront's own JSON endpoint
(``/api/collections/products?collection=<handle>&cursor=<cursor>``) and
product pages live at ``/product/<handle>``.

This scraper keeps the ``ShopifyJsonScraper`` machinery but overrides the
listing fetch to pull from the storefront API and normalize each product
into the classic Shopify ``products.json`` shape the rest of the pipeline
expects.

Bean URLs keep the *legacy* collection paths
(``/collections/filter-beans/products/<handle>`` etc.) so that existing
database rows, diffjson stock updates and roast-profile detection
(``"filter-beans"`` / ``"espresso-beans"`` in the URL) keep matching
historical identities.
"""

import logging
import re
from typing import Any
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from ..schemas import CoffeeBean
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)

STOREFRONT_API_URL = "https://www.aprilcoffeeroasters.com/api/collections/products"

# Legacy URL segment -> storefront API collection handles whose products are
# published under that legacy identity prefix.
#
# The legacy segment only acts as the URL identity prefix (the legacy pages no
# longer exist); it is chosen to match the collections the products
# historically appeared in so stock updates and roast-profile detection keep
# working.
#
# Collection coverage (verified live 2026-11): ``filter-coffee`` and
# ``espresso-coffee`` hold the core roast-specific beans, ``limited-coffee``
# the limited geshas, ``samplebox`` the sample box, ``organic-coffee`` the
# organic bean, ``projects`` the Sustainable Profile beans, and
# ``filter-drip-packs`` the single-serve drip packs.
COLLECTIONS: dict[str, list[str]] = {
    "filter-beans": ["filter-coffee", "samplebox", "organic-coffee", "filter-drip-packs"],
    "espresso-beans": ["espresso-coffee", "limited-coffee", "projects"],
}

_LEGACY_URL_RE = re.compile(r"/collections/([^/]+)/products\.json")


@register_scraper(
    name="april-coffee",
    display_name="April Coffee",
    roaster_name="April Coffee",
    website="https://www.aprilcoffeeroasters.com",
    description="Specialty coffee roastery based in Copenhagen, Denmark",
    requires_api_key=True,
    currency="DKK",  # Danish Krone
    country="Denmark",
    status="available",
)
class AprilCoffeeScraper(ShopifyJsonScraper):
    """Scraper for April Coffee (aprilcoffeeroasters.com).

    The storefront is a custom Next.js app backed by the Shopify Storefront
    API; products are fetched from its JSON endpoint and normalized into the
    Shopify ``products.json`` shape used by ``ShopifyJsonScraper``.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize April Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="April Coffee",
            base_url="https://www.aprilcoffeeroasters.com",
            # Legacy collection URLs: identity prefixes only (they 404 on the
            # new storefront). Listing data comes from the storefront API via
            # the ``_fetch_all_shopify_products`` override below.
            products_json_urls=[
                f"https://www.aprilcoffeeroasters.com/collections/{legacy}/products.json" for legacy in COLLECTIONS
            ],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude non-coffee products (subscriptions, merch, ...). The
        # ``projects`` collection also carries a mug and a bandana that would
        # otherwise reach the AI extractor every session.
        self.exclude_slugs = [
            "subscription",
            "gift",
            "giftcard",
            "merchandise",
            "equipment",
            "brew-gear",
            "-merch",
            "from-nerd-to-pro",
            "bandana",
            "-mug",
        ]

        # The currency is fixed (DKK); pin it so the base class skips its
        # currency-detection fetch of the (now 404) legacy collection page.
        self.store_currency = "DKK"
        self._currency_detected = True

        self._api_handles_by_legacy_segment = {legacy: handles for legacy, handles in COLLECTIONS.items()}

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def _fetch_all_shopify_products(self, products_json_url: str) -> list[dict[str, Any]]:
        """Fetch all products from the April storefront API for a legacy URL.

        Overrides the classic ``products.json`` pagination (which 404s on the
        new storefront) with cursor pagination against
        ``/api/collections/products``. On failure the listing URL is recorded
        in ``_failed_listing_urls`` so out-of-stock updates are suppressed for
        the session (false-delisting guard), mirroring the base behavior.

        Args:
            products_json_url: Legacy ``/collections/<segment>/products.json`` URL

        Returns:
            List of product dictionaries in the classic Shopify products.json shape
        """
        match = _LEGACY_URL_RE.search(products_json_url)
        api_handles = self._api_handles_by_legacy_segment.get(match.group(1)) if match else None
        if not api_handles:
            logger.error(f"Unknown April Coffee collection URL: {products_json_url}")
            if products_json_url not in self._failed_listing_urls:
                self._failed_listing_urls.append(products_json_url)
            return []

        all_products: list[dict[str, Any]] = []
        for api_handle in api_handles:
            cursor: str | None = None
            while True:
                params: dict[str, str] = {"collection": api_handle}
                if cursor:
                    params["cursor"] = cursor
                url = f"{STOREFRONT_API_URL}?{urlencode(params)}"
                logger.info(f"Fetching April Coffee storefront products: {url}")
                try:
                    response = await self.client.get(url)
                    response.raise_for_status()
                    data = response.json()
                except Exception as e:
                    logger.error(f"Failed to fetch April Coffee storefront API {url}: {e}")
                    if products_json_url not in self._failed_listing_urls:
                        self._failed_listing_urls.append(products_json_url)
                    return []

                products = data.get("products") or []
                all_products.extend(self._normalize_storefront_product(p) for p in products)

                page_info = data.get("pageInfo") or {}
                cursor = page_info.get("endCursor")
                if not page_info.get("hasNextPage") or not cursor:
                    break

        return all_products

    def _normalize_storefront_product(self, product: dict[str, Any]) -> dict[str, Any]:
        """Normalize a storefront API product into the Shopify products.json shape.

        The storefront API exposes a price range and a single availability
        flag instead of a variant list; a synthesized single variant keeps the
        downstream price/stock handling unchanged.

        Args:
            product: Product dictionary from the storefront API

        Returns:
            Product dictionary in the classic Shopify products.json shape
        """
        price_range = product.get("priceRange") or {}
        min_price = (price_range.get("minVariantPrice") or {}).get("amount")
        available = bool(product.get("availableForSale", False))
        featured = product.get("featuredImage") or {}
        image_url = featured.get("url")

        normalized: dict[str, Any] = {
            "id": product.get("id"),
            "title": product.get("title"),
            "handle": product.get("handle"),
            "description": product.get("description"),
            "body_html": product.get("descriptionHtml") or product.get("description"),
            "tags": product.get("tags") or [],
            "options": [
                {"name": opt.get("name"), "values": opt.get("values") or []} for opt in product.get("options") or []
            ],
            # Synthesized variant: the API only exposes price range + availability.
            "variants": [{"title": "Default", "price": min_price, "available": available}],
            "available": available,
            "images": [{"src": image_url}] if image_url else [],
            "image": image_url,
            # Roaster-written farm/brew notes, useful AI extraction context.
            "supplier_information": product.get("supplierInformation") or {},
            "recommendations": product.get("recommendations") or {},
        }
        return normalized

    async def fetch_page_with_screenshot(
        self, url: str, retries: int = 0, use_playwright: bool = False
    ) -> tuple[BeautifulSoup | None, bytes | None]:
        """Rewrite legacy product URLs to the real storefront pages before fetching.

        The legacy ``/collections/<segment>/products/<handle>`` identity URLs
        404 on the new storefront; the live pages live at
        ``/product/<handle>``. Used for the product-page caching pass (and any
        other page fetch) so Playwright isn't wasted on 404s.

        Args:
            url: Page URL
            retries: Number of retries attempted
            use_playwright: Whether to use Playwright instead of httpx

        Returns:
            Tuple of (BeautifulSoup object, screenshot bytes) or (None, None)
        """
        url = re.sub(r"/collections/[^/]+/products/", "/product/", str(url))
        return await super().fetch_page_with_screenshot(url, retries=retries, use_playwright=use_playwright)

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Override to ensure currency and roast profiles based on URL.

        Bean URLs carry the legacy collection segments (see ``COLLECTIONS``);
        the new storefront handles are also accepted in case the URL scheme
        moves to the live handles later.
        """
        bean.currency = "DKK"
        url = str(bean.url)
        if "filter-beans" in url or "filter-coffee" in url:
            bean.roast_profile = "Filter"
        elif "espresso-beans" in url or "espresso-coffee" in url:
            bean.roast_profile = "Espresso"

        return super().postprocess_extracted_bean(bean)
