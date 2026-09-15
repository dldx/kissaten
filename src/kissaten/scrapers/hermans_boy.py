"""Herman's Boy Coffee scraper implementation with AI-powered extraction (Square Online).

Herman's Boy Coffee (hermans-boy.square.site) is a Michigan (US) coffee roaster
and tea retailer running a Square Online storefront (the classic Weebly /
"editmysite" commerce stack).

Platform notes from curl-first discovery (2026-09):
- Product cards on category pages are JS-rendered without anchor hrefs, so the
  listing HTML exposes no product links. Square/Weebly publishes a public store
  JSON API instead (``cdn5.editmysite.com/app/store/api/v28/...``) which powers
  the storefront itself: category listing, per-product detail and per-SKU prices.
- ``sitemap.xml`` lists 694 product URLs (coffee, tea, merch, equipment) with no
  way to tell the categories apart in-slug, so the category API is used for
  discovery: the "Coffee" category (T7MSYPDOIACMII5LSZI33SOE) is the parent of
  the ``Blends`` / ``Coffees of Origin`` / ``Dark Roast Coffee`` /
  ``Flavored Coffee`` subcategories and holds all 71 coffee products.
- Sold-out products are marked by ``badges.out_of_stock`` in the store API.
- Product detail pages are heavy (~3 MB) and render lazily after ~15 s, but the
  same content is available from the per-product detail + SKU API endpoints
  (description, option sets, per-size SKUs with prices). This scraper therefore
  rebuilds a compact HTML summary from the API and hands *that* to the AI
  extractor, avoiding Playwright entirely.
"""

import logging
import re

from bs4 import BeautifulSoup

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)

STORE_API_BASE = "https://cdn5.editmysite.com/app/store/api/v28/editor/users/154583705/sites/306625593761697154"
STORE_LOCATION_ID = "LWSPP4QXWWFGN"

# Coffee catalogue. The first is the parent category (71 products); the others
# are its subcategories and are included so a future re-categorisation cannot
# silently drop products. Overlap is removed by the URL de-duplication.
COFFEE_CATEGORY_IDS = {
    "coffee": "T7MSYPDOIACMII5LSZI33SOE",
    "blends": "OC6QVH3TXFUWOWT4SMKOZ6I2",
    "coffees-of-origin": "VJVKCOBHRINNR5KQO4YMBRZW",
    "dark-roast-coffee": "ELBNZAEZAL2GINGOSJYRE6GR",
    "flavored-coffee": "VHXVGK36N5LELKPTKQ63A23I",
}

_PRODUCTS_PER_PAGE = 50
_MAX_PAGES = 10

# Size fragments such as "1/2 lb bag", "1 lb bag", "12 oz", "250 g".
_SIZE_RE = re.compile(r"(\d+(?:\.\d+)?|\d+/\d+)\s*(lbs?|pounds?|oz|ounces?|kgs?|kilograms?|g|grams?)\b", re.IGNORECASE)
_UNIT_GRAMS = {
    "lb": 453.59237,
    "lbs": 453.59237,
    "pound": 453.59237,
    "pounds": 453.59237,
    "oz": 28.349523,
    "ounce": 28.349523,
    "ounces": 28.349523,
    "kg": 1000.0,
    "kgs": 1000.0,
    "kilogram": 1000.0,
    "kilograms": 1000.0,
    "g": 1.0,
    "gram": 1.0,
    "grams": 1.0,
}


def _parse_weight_grams(text: str) -> int | None:
    """Parse a bag-size fragment (e.g. "1/2 lb bag", "250 g") into grams.

    Args:
        text: SKU name or option value containing a size.

    Returns:
        Weight in grams, or None when no size could be parsed or it falls
        outside the schema's accepted 10 g – 10 kg range.
    """
    match = _SIZE_RE.search(text or "")
    if not match:
        return None

    raw, unit = match.group(1), match.group(2).lower()
    if "/" in raw:
        numerator, denominator = raw.split("/", 1)
        try:
            amount = float(numerator) / float(denominator)
        except (ValueError, ZeroDivisionError):
            return None
    else:
        amount = float(raw)

    grams = int(round(amount * _UNIT_GRAMS[unit]))
    if grams <= 10 or grams > 10000:
        return None
    return grams


@register_scraper(
    name="hermans-boy",
    display_name="Herman's Boy Coffee",
    roaster_name="Herman's Boy Coffee",
    website="https://hermans-boy.square.site",
    description="Coffee roaster and tea retailer in Rockford, Michigan, United States (Square Online).",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class HermansBoyScraper(BaseScraper):
    """Scraper for Herman's Boy Coffee (hermans-boy.square.site) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize the Herman's Boy Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Herman's Boy Coffee",
            base_url="https://hermans-boy.square.site",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = None
        try:
            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
        except ValueError:
            logger.warning("Google API key not configured. AI extraction will not be available.")

    async def get_store_urls(self) -> list[str]:
        """Get the Square store API listing URLs for the coffee categories.

        Product cards on the category pages carry no hrefs (JS-rendered), so the
        store's own JSON API is used for discovery.

        Returns:
            List of category product-API URLs.
        """
        return [
            f"{STORE_API_BASE}/products?page=1&per_page={_PRODUCTS_PER_PAGE}"
            f"&sort_by=name&sort_order=asc&categories[]={category_id}&include=images,categories"
            for category_id in COFFEE_CATEGORY_IDS.values()
        ]

    async def _fetch_json(self, url: str) -> dict | None:
        """Fetch and decode a store API JSON document.

        Args:
            url: Absolute API URL.

        Returns:
            Parsed JSON object or None when the fetch failed.
        """
        try:
            response = await self.client.get(url)
        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            return None

        if response.status_code != 200:
            logger.warning(f"Store API returned HTTP {response.status_code} for {url}")
            return None

        try:
            return response.json()
        except ValueError as e:
            logger.warning(f"Store API did not return JSON for {url}: {e}")
            return None

    # Sold-out detection: Square store API `badges.out_of_stock` flag.
    # Products flagged out of stock (or hidden from the storefront via
    # `visibility`) are skipped before the coffee-URL filter, so an
    # out-of-stock product is recorded as a stock update rather than a listing.
    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract in-stock coffee product URLs from a Square store API category listing.

        Args:
            store_url: Category products-API URL.

        Returns:
            List of in-stock product URLs.
        """
        product_urls: list[str] = []
        seen: set[str] = set()

        for page in range(1, _MAX_PAGES + 1):
            page_url = re.sub(r"([?&]page=)\d+", rf"\g<1>{page}", store_url)
            payload = await self._fetch_json(page_url)
            if payload is None:
                # A failed catalogue fetch must not be read as "everything sold
                # out": return nothing so the base class records the listing
                # failure and skips out-of-stock updates.
                return []

            products = payload.get("data") or []
            for product in products:
                url = product.get("absolute_site_link")
                if not url:
                    continue

                if product.get("visibility") != "visible":
                    logger.debug(f"Skipping non-visible product: {url}")
                    continue
                if (product.get("badges") or {}).get("out_of_stock"):
                    logger.debug(f"Skipping sold-out product: {url}")
                    continue

                url = url.split("?")[0].split("#")[0]
                if not self.is_coffee_product_url(url, required_path_patterns=["/product/"]):
                    continue

                if url not in seen:
                    seen.add(url)
                    product_urls.append(url)

            pagination = (payload.get("meta") or {}).get("pagination") or {}
            current_page = pagination.get("current_page") or page
            total_pages = pagination.get("total_pages") or 1
            if current_page >= total_pages or not products:
                break

        logger.info(f"Found {len(product_urls)} in-stock coffee product URLs from {store_url}")
        return product_urls

    @staticmethod
    def _product_id_from_url(url: str) -> str | None:
        """Extract the Square product id (last URL path segment) from a product URL."""
        path = url.split("?")[0].split("#")[0].rstrip("/")
        candidate = path.rsplit("/", 1)[-1]
        return candidate or None

    async def _fetch_product_summary_html(self, product_url: str) -> str | None:
        """Build a compact HTML summary of a product from the Square store API.

        Square Online detail pages are multi-megabyte JS apps while the same
        data is available as two small JSON documents (product detail + SKUs).
        Rendering the API data into a tiny HTML document lets the standard AI
        extractor work on clean, complete input without Playwright.

        Args:
            product_url: Public product URL.

        Returns:
            HTML string or None when the product could not be loaded.
        """
        product_id = self._product_id_from_url(product_url)
        if not product_id:
            return None

        detail_url = (
            f"{STORE_API_BASE}/store-locations/{STORE_LOCATION_ID}/products/{product_id}"
            "?include=images,options,modifiers,category,media_files,fulfillment_availability"
        )
        skus_url = (
            f"{STORE_API_BASE}/store-locations/{STORE_LOCATION_ID}/products/{product_id}"
            "/skus?page=1&per_page=100&include=image,media_files,product"
        )

        detail = await self._fetch_json(detail_url)
        if detail is None:
            return None
        product = detail.get("data") if isinstance(detail.get("data"), dict) else detail

        skus_payload = await self._fetch_json(skus_url) or {}
        skus = skus_payload.get("data") or []

        name = product.get("name") or ""
        description = product.get("short_description") or product.get("og_description") or ""
        description_text = BeautifulSoup(description, "lxml").get_text(" ", strip=True)

        options_lines = []
        for option in (product.get("options") or {}).get("data", []) or []:
            choices = ", ".join(str(choice) for choice in option.get("choice_order") or [])
            if choices:
                options_lines.append(f"{option.get('name')}: {choices}")

        variant_lines = []
        for sku in skus:
            sku_name = sku.get("name") or ""
            price = (sku.get("price") or {}).get("current")
            price_formatted = (sku.get("price") or {}).get("current_formatted") or ""
            weight = _parse_weight_grams(sku_name)
            weight_part = f" ({weight} g)" if weight else ""
            if price is None:
                continue
            variant_lines.append(f"- {sku_name}{weight_part} | Price: {price_formatted or price} USD")

        image_url = ""
        images = (product.get("images") or {}).get("data") or []
        if images:
            image_url = images[0].get("absolute_url") or ""

        parts = [f"<h1>{name}</h1>"]
        if description_text:
            parts.append(f"<div class='product-description'>{description_text}</div>")
        if options_lines:
            parts.append("<div class='product-options'>" + "<br>".join(options_lines) + "</div>")
        if variant_lines:
            parts.append("<div class='product-variants'><h2>Variants</h2>" + "<br>".join(variant_lines) + "</div>")
        if image_url:
            parts.append(f"<img src='{image_url}' alt='{name}'>")

        logger.debug(f"Built Square API summary for {product_url} ({len(skus)} SKUs)")
        return "<html><body>" + "".join(parts) + "</body></html>"

    async def fetch_page(self, *args, **kwargs):
        """Fetch a page, serving product detail pages from the Square store API.

        Args:
            *args: Positional arguments forwarded to the base fetch_page.
            **kwargs: Keyword arguments forwarded to the base fetch_page.

        Returns:
            BeautifulSoup object or None if the fetch failed.
        """
        url = kwargs.get("url") or (args[0] if args else "")
        if url and "/product/" in url:
            summary = await self._fetch_product_summary_html(url)
            if summary:
                return BeautifulSoup(summary, "lxml")
            logger.warning(f"Could not build API summary for {url}; falling back to HTML fetch")
        return await super().fetch_page(*args, **kwargs)

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction.

        Args:
            product_urls: List of URLs for new products.

        Returns:
            List of newly scraped CoffeeBean objects.
        """
        if not product_urls:
            return []

        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=False,
            use_optimized_mode=False,
            translate_to_english=False,
        )

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Pin the store currency (the registry lookup by display name can fall back to GBP)."""
        bean.currency = "USD"
        return bean
