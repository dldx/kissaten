"""Delicate Coffee Roasters scraper implementation with Shopify JSON extraction.

Delicate Coffee (delicate.coffee) is a two-person micro-roastery in Chicago,
Illinois — an artist and a roaster — selling seasonal single-origin lots. The
store is Shopify (the privacy policy says "delicate coffee roasters is powered
by Shopify"; no myshopify.com domain is needed).

Scope: ``/collections/shop`` is the curated all-coffee collection and is the
only products.json URL we read. Both ``/collections/shop/products.json`` and the
site-wide ``/products.json`` return valid JSON, but the curated collection is
the deliberate scope: the site also runs ``/collections/archive`` with retired
lots, which must NOT be filtered out as "archive" noise.

Traps:

* ``product_type`` is ``""`` and ``tags`` is ``[]`` on every current product, so
  neither can be used to select coffee. Filtering is therefore slug/title based,
  delegated to the base-class URL/name heuristics plus a small exclude list.
* The product sitemap carries ~20 product URLs including four retired art
  products ``print 1``..``print 4`` ("coffee bud prints", in
  ``/collections/prints``). The curated ``shop`` collection already excludes
  them, but ``"print"`` is in ``exclude_slugs`` as a belt-and-braces guard
  (substring match against the handle).
* There are no tasting kits, gear, subscriptions or gift cards on this store, so
  no kit/review special-casing is needed.

Product shape: everything is 125 g whole bean at a flat USD 19.00, one default
variant. All the coffee data lives in ``body_html`` as consistent labelled
lines — ``From : Bona Zuria, Sidama, Ethiopia (2100-2200 MASL)`` /
``Varietal : Mixed JARC (74158, ...)`` / ``Process : White Honey`` /
``Notes : Golden Raspberry, Lemon Sugar, Lilac`` — followed by ``Processing``,
``Taste`` and producer/co-op prose sections. Product titles are concise lot
names, often with a grading or prep suffix ("kii AA", "getuya AA",
"kathima AB - rested", "bare - special prep").

Because ``price`` is optional on ``CoffeeBean`` and JSON-only mode never shows
the extractor a rendered price, the extractor decided per product whether to
report it — and on 3 of the 6 live beans it reported only ``price_options``.
``_backfill_price_from_shopify_product`` therefore re-derives the top-level
price from ``variants[0]["price"]``, which is authoritative and present on
every product.
"""

import logging
import re
from typing import Any

from pydantic import ValidationError

from ..schemas import CoffeeBean
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="delicate-coffee",
    display_name="Delicate Coffee",
    roaster_name="Delicate Coffee",
    website="https://delicate.coffee",
    description="Chicago two-person micro-roastery of an artist and a roaster, selling seasonal "
    "125 g single-origin lots with long producer and co-op write-ups.",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class DelicateCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Delicate Coffee (delicate.coffee) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Delicate Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Delicate Coffee",
            base_url="https://delicate.coffee",
            products_json_urls=["https://delicate.coffee/collections/shop/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Pin the home-market currency: this is a US storefront selling in USD,
        # and runtime currency detection falls back to the display name (which
        # would not resolve) or to a geo-converted Shopify Markets price.
        self.store_currency = "USD"
        self._currency_detected = True

        # product_type and tags are empty on every current product, so selection
        # is slug based. The only non-coffee handles that ever reach us are the
        # four retired "coffee bud prints" art products (print 1..print 4); the
        # curated shop collection already excludes them, so this is a guard
        # rather than the primary filter. Retired *coffees* in
        # /collections/archive are deliberately NOT excluded.
        self.exclude_slugs = [
            "print",  # retired coffee bud art prints (print-1..print-4)
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

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Pin the currency to USD and backfill the price from the product JSON.

        The store only ever prices in USD (flat 19.00 for a 125 g bag), but the
        base-class detection can pick up a converted price when Shopify Markets
        geo-routes the caller, so make the home currency authoritative. Every
        ``price_options[].currency`` is pinned to the same code: the extractor
        leaves it unset or guesses, and a mismatched entry poisons ``price_usd``
        normalization at refresh time.

        The top-level ``price`` is then backfilled from the authoritative
        products.json variant price — see
        ``_backfill_price_from_shopify_product``.
        """
        bean.currency = "USD"
        for price_option in bean.price_options or []:
            price_option.currency = "USD"
        self._backfill_price_from_shopify_product(bean)
        return super().postprocess_extracted_bean(bean)

    def _shopify_product_for_bean(self, bean: CoffeeBean) -> dict[str, Any] | None:
        """Look the bean's products.json entry up by its product URL.

        ``_shopify_product_data`` is keyed by the formatted (canonicalized)
        product URL that ``_extract_product_urls_from_store`` built, and
        ``bean.url`` is that same URL as handed to the extractor. ``HttpUrl``
        percent-encodes non-ASCII handles while products.json returns them raw,
        so a miss retries on the decoded form — the same trick
        ``ShopifyJsonScraper.create_diffjson_stock_updates`` uses to match
        ``_shopify_stock_status`` against stored bean files.

        Args:
            bean: CoffeeBean whose product payload is wanted

        Returns:
            The products.json product dict, or None when the URL is unknown.
        """
        url = str(bean.url) if bean.url else ""
        if not url:
            return None

        product = self._shopify_product_data.get(url)
        if product is not None:
            return product

        decoded_url = self._normalize_url(url)
        for key, candidate in self._shopify_product_data.items():
            if self._normalize_url(key) == decoded_url:
                return candidate
        return None

    @staticmethod
    def _variant_price(product: dict[str, Any]) -> float | None:
        """Read the authoritative price out of a products.json product.

        Every Delicate coffee is one default variant, but the walk is defensive:
        an available variant wins over a sold-out one, non-numeric and
        non-positive amounts are skipped (the retired art prints carry
        ``"0.00"``), and a product-level ``price``/``prices.price`` is accepted
        for payloads that carry no variants at all.

        Args:
            product: products.json product dict

        Returns:
            The variant price, or None when the payload states none.
        """
        variants = [v for v in product.get("variants") or [] if isinstance(v, dict)]
        for pool in ([v for v in variants if v.get("available")], variants):
            for variant in pool:
                try:
                    value = float(variant.get("price"))
                except (TypeError, ValueError):
                    continue
                if value > 0:
                    return value

        prices = product.get("prices")
        raw = prices.get("price") if isinstance(prices, dict) else product.get("price")
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return None
        return value if value > 0 else None

    def _backfill_price_from_shopify_product(self, bean: CoffeeBean) -> None:
        """Backfill ``bean.price`` from the products.json variant price.

        JSON-only mode (``scrape_product_pages=False``) never sees a rendered
        price, so the extractor decides whether the optional top-level ``price``
        field is set at all — and it omitted it on 3 of the 6 live beans even
        though it had reported the correct 19.00 in ``price_options``. Those
        beans were stored with ``price: null`` and normalize to a null
        ``price_usd`` at refresh time. The variant price is deterministic and
        present on every product, so it is the authoritative source; modelled on
        ``ShopifyJsonScraper._backfill_image_url_from_shopify_product``.

        The weight is *not* backfilled: the variant carries ``"grams": 0`` and
        the title ``"Default Title"``, so the only honest source for the 125 g
        bag size remains the extractor.

        ``CoffeeBean`` sets ``validate_assignment=True``, so the assignment
        re-runs the ``check_prices`` per-gram range validator — 19.00 for 125 g
        is $0.15/g, comfortably inside the accepted band. A value that fails is
        logged and dropped rather than failing the whole extraction.

        Args:
            bean: CoffeeBean to backfill
        """
        if bean.price is not None:
            return

        product = self._shopify_product_for_bean(bean)
        if not product:
            return

        price = self._variant_price(product)
        if price is None:
            return

        try:
            bean.price = price
            logger.info(f"Backfilled price {price} from products.json variant for bean {bean.name!r}")
        except ValidationError as e:
            logger.warning(f"Rejected products.json price {price} for bean {bean.name!r}: {e}")

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from the curated shop collection.

        ``/collections/shop`` is already coffee-only, and ``product_type`` is
        empty on every product, so the only explicit gate is the retired
        art-print slug exclusion; the base-class URL/name filters handle the
        rest. Retired coffees living in ``/collections/archive`` are out of
        scope of this collection and are not separately excluded.
        """
        products = await self._fetch_all_shopify_products(store_url)
        found_urls = []

        for product in products:
            handle = product.get("handle")
            if not handle:
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
