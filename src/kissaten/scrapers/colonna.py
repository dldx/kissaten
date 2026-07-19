"""Colonna Coffee scraper implementation with Shopify JSON extraction.

Colonna keeps stable product slugs (e.g. ``beans-foundation``) but rotates the
underlying coffee content monthly. To detect these content changes, the
``body_html`` text hash is appended to each product URL as a fragment, so a
content rotation produces a new URL identity. This lets the base ``scrape()``
flow treat rotated beans as NEW products (full re-extraction) while leaving
unchanged beans as EXISTING (stock-status diffjson only).
"""

import hashlib
import logging

from bs4 import BeautifulSoup

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="colonna",
    display_name="Colonna",
    roaster_name="Colonna",
    website="https://colonnacoffee.com",
    description="Bath-based roastery founded in 2015, known for scientific research on "
    "water science, frozen grinding, and sustainability, and for rotating single-origin coffees.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class ColonnaScraper(ShopifyJsonScraper):
    """Scraper for Colonna (colonnacoffee.com) using Shopify products.json.

    Colonna rotates the actual coffee under stable product slugs (e.g.
    ``beans-foundation`` may be Mexican this month and Colombian next month).
    To detect content rotation, we append a hash of the ``body_html`` text as a
    URL fragment. When the coffee rotates, the fragment changes, producing a
    new URL identity — triggering full re-extraction while marking the prior
    record as out-of-stock via the standard diffjson flow.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Colonna scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Colonna",
            base_url="https://colonnacoffee.com",
            products_json_urls=["https://colonnacoffee.com/collections/beans/products.json"],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude non-coffee products (subscriptions, gift cards, equipment, etc.)
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
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
            # Colonna bundles (multi-bean packs, not single-origin slots)
            "beans-all-3",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def _get_excluded_url_patterns(self) -> list[str]:
        """Remove ``discovery`` from the base exclusion list.

        The base class excludes URLs containing ``discovery`` to filter out
        "discovery pack" / subscription products. Colonna has a ``beans-discovery``
        slot that is a legitimate rotating single-origin coffee, not a pack,
        so we drop that one pattern while keeping all other base exclusions.
        """
        return [p for p in super()._get_excluded_url_patterns() if p != "discovery"]

    def _compute_body_html_hash(self, product: dict) -> str:
        """Compute a stable hash of the product's body_html text content.

        Hashes the *text* of ``body_html`` (not the raw HTML) so that
        Shopify WYSIWYG reformatting (tag swapping, attribute reordering) does
        not trigger spurious re-extraction. Only genuine content changes
        (origin country, farm, process, tasting notes, etc.) produce a new
        hash.

        Args:
            product: Shopify product dictionary.

        Returns:
            16-character hex hash, or ``"empty"`` if body_html is missing.
        """
        body_html = product.get("body_html", "") or ""
        if not body_html.strip():
            return "empty"
        soup = BeautifulSoup(body_html, "lxml")
        text = soup.get_text(separator=" ", strip=True).lower()
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from a Shopify products.json endpoint.

        Overrides the base implementation to append a ``#body_html_hash=<hash>``
        fragment to each URL before storing it in ``_shopify_product_data``.
        This makes URL identity include content identity, so the base
        ``scrape()`` flow automatically treats content rotations as new
        products (full re-extraction) while leaving unchanged products for
        stock-status diffjson updates.

        Args:
            store_url: URL of the products.json endpoint.

        Returns:
            List of product URLs (with content-hash fragment appended).
        """
        products = await self._fetch_all_shopify_products(store_url)
        found_urls: list[str] = []
        base_path = store_url.replace("/products.json", "")

        for product in products:
            handle = product.get("handle")
            if not handle:
                continue

            if any(slug in handle for slug in self.exclude_slugs):
                logger.debug(f"Skipping excluded product slug: {handle}")
                continue

            url = f"{base_path}/products/{handle}"

            # Append body_html hash as URL fragment so content rotation
            # produces a new URL identity (triggers full re-extraction).
            body_hash = self._compute_body_html_hash(product)
            url = f"{url}#body_html_hash={body_hash}"

            # Store metadata for later enrichment and stock status
            self._shopify_product_data[url] = product

            # A product is in stock if any of its variants are available
            is_available = any(v.get("available", False) for v in product.get("variants", []))
            self._shopify_stock_status[url] = is_available

            # Filter out non-coffee products using base class logic
            if self.is_coffee_product_url(url) and self.is_coffee_product_name(product.get("title", "")):
                found_urls.append(url)

        return found_urls
