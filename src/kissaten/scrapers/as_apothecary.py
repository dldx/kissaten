"""A S Apothecary scraper implementation with Shopify JSON extraction.

A S Apothecary (asapoth.com) is a Shopify MIXED store: ~87 products of which
only 7 are single-origin coffee — the rest are skincare/soap/tea/merch
products. There is no curated coffee collection, and ``product_type`` is
unreliable (only ``colombia-decaf-popayan`` carries type ``"coffee"``; the
other six coffees have empty product_type).

So ``_extract_product_urls_from_store`` is a strict include-filter:
a product is kept only if its Shopify ``product_type`` is coffee, OR its title
matches the single-origin pattern ``<Country> - <name>`` (e.g.
"Ethiopia - Taferi Kela", "Colombia DECAF - Popayan"). The robust country
regex below matches those seven beans and nothing in the skincare catalog.

Coffee handles (verified 2026-08): ethiopia-taferi-kela, colombia-asorcafe,
peru-bellavista, brazil-terras-altas, el-salvador-el-borbollon,
colombia-anserma-chapata, colombia-decaf-popayan. If the country regex ever
stops matching a future coffee, add its handle to the fallback allow-list
below.

The coffee body_html is rich (origin, tasting notes, cupping score, altitude,
process), so the scraper runs JSON-only (``scrape_product_pages=False``,
``use_optimized_mode=True``) with the injected Shopify context.
"""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)

# Countries/regions that start the single-origin title pattern "<Country> - <name>".
_ORIGIN_COUNTRIES = (
    r"Ethiopia|Colombia|Peru|Brazil|El Salvador|Guatemala|Costa Rica|Kenya|Rwanda|Burundi|"
    r"Mexico|Panama|Honduras|Nicaragua|Bolivia|Ecuador|Jamaica|Indonesia|India|Papua|"
    r"Vietnam|Tanzania|Uganda|Congo|Yemen|Sumatra|Java"
)
# "<Country> [optional words like DECAF] - <name>"
_SINGLE_ORIGIN_TITLE_RE = re.compile(
    rf"^\s*({_ORIGIN_COUNTRIES})(\s+[A-Za-z]+)*?\s*-\s+", re.IGNORECASE
)


@register_scraper(
    name="a-s-apothecary",
    display_name="A S Apothecary",
    roaster_name="A S Apothecary",
    website="https://asapoth.com",
    description=(
        "Isle of Harris apothecary that also roasts a small selection of "
        "single-origin coffees, sold alongside skincare products."
    ),
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class ASApothecaryScraper(ShopifyJsonScraper):
    """Scraper for A S Apothecary (asapoth.com) using Shopify products.json.

    Mixed store: the default products.json mixes coffee with ~80 skincare
    items, so ``_extract_product_urls_from_store`` is overridden to include
    ONLY the coffee products (product_type coffee or a country-prefixed title).
    """

    def __init__(self, api_key: str | None = None):
        """Initialize A S Apothecary scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="A S Apothecary",
            base_url="https://asapoth.com",
            products_json_urls=["https://asapoth.com/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The coffee bodies carry full origin/tasting/cupping info; run
        # JSON-only with the injected Shopify context.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Fallback allow-list of the 7 verified coffee handles, in case the
        # title regex stops matching a renamed product.
        self._coffee_handles = {
            "ethiopia-taferi-kela",
            "colombia-asorcafe",
            "peru-bellavista",
            "brazil-terras-altas",
            "el-salvador-el-borbollon",
            "colombia-anserma-chapata",
            "colombia-decaf-popayan",
        }

        # No exclude_slugs: the include-filter below is the only gate, and we
        # must NOT exclude tasting-kit/sampler tokens (base flagging handles
        # them). The skincare products simply never match the filter.

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize A S Apothecary URLs by removing collection segments."""
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs, keeping ONLY the coffee products.

        The default base-class filter (``is_coffee_product_url`` +
        ``is_coffee_product_name``) is intentionally conservative and would
        pass the skincare catalog, so we include-fillter on coffee explicitly:
        keep a product when ``product_type`` is coffee or the title matches the
        "<Country> - <name>" single-origin pattern.
        """
        products = await self._fetch_all_shopify_products(store_url)
        found_urls = []

        for product in products:
            handle = product.get("handle")
            if not handle:
                continue

            title = product.get("title", "") or ""
            product_type = (product.get("product_type") or "").strip().lower()

            # Include-filter: coffee product_type or single-origin title pattern.
            if product_type == "coffee":
                pass
            elif _SINGLE_ORIGIN_TITLE_RE.match(title):
                pass
            elif handle in self._coffee_handles:
                pass
            else:
                logger.debug(f"Skipping non-coffee product: {handle} ({title!r})")
                continue

            # Build product URL using the base of the products.json URL.
            base_path = store_url.replace("/products.json", "")
            url = f"{base_path}/products/{handle}"

            # Preprocess the URL (strip any collection segments).
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
