"""WatchHouse coffee scraper using Shopify products.json with title disambiguation."""

import logging
import re
import unicodedata

from bs4 import BeautifulSoup

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="watchhouse",
    display_name="WatchHouse",
    roaster_name="WatchHouse",
    website="https://watchhouse.com",
    description="Speciality coffee roaster and café group based in London, United Kingdom.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class WatchHouseScraper(ShopifyJsonScraper):
    """Scraper for WatchHouse using Shopify products.json.

    WatchHouse rotates coffees seasonally under stable product handles
    (``rituals-filter``, ``ventures-filter``, ``horizons-filter``, …): at any
    given time each handle maps to exactly one coffee, but the same handle is
    reused for a different bean every few months. The Shopify product title
    tracks the current bean (e.g. ``Nguvu Washed.``), so we disambiguate by
    emitting ``<product_url>#<title-slug>`` — one URL per product, with the
    slugified product title as the fragment.

    When a coffee rotates, the title (and therefore the fragment) changes,
    producing a new URL: the new bean is scraped fresh while the old URL
    drops out of products.json and the base scraper's stock-update logic
    marks the previous bean as out-of-stock. This preserves history instead
    of overwriting the same record on every rotation. The multiple images
    attached to a product are marketing shots of the same bean, so we do NOT
    use the per-image disambiguation that the Wide Awake scraper relies on.

    The product page is filtered down to ``div.main-product__grid`` before
    AI extraction (no screenshot — the grid plus injected Shopify JSON is
    enough context for the extractor).
    """

    def __init__(self, api_key: str | None = None):
        """Initialize WatchHouse scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="WatchHouse",
            base_url="https://watchhouse.com",
            products_json_urls=[
                "https://watchhouse.com/collections/coffee/products.json",
            ],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude non-coffee products (subscriptions, bundles, gift sets, cold
        # brew in a can, and the multi-roaster subscription box).
        self.exclude_slugs = [
            "subscription",
            "bundle",
            "1kg",
            "nitro-cold-brew",
            "roasters-spotlight",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Canonicalize product URLs to ``<base_url>/products/<handle>``.

        The products.json endpoint lives under ``/collections/coffee``, so
        the default URL construction yields ``/collections/coffee/products/…``.
        Historical bean data uses the canonical ``/products/<handle>`` form,
        so we strip any ``/collections/<slug>`` segment here. Any ``#fragment``
        (used for title disambiguation, see ``_extract_product_urls_from_store``)
        is preserved.
        """
        if "/products/" in url:
            handle_and_rest = url.split("/products/")[-1]
            fragment = ""
            if "#" in handle_and_rest:
                handle, fragment = handle_and_rest.split("#", 1)
                fragment = "#" + fragment
            else:
                handle = handle_and_rest
            return f"{self.base_url}/products/{handle}{fragment}"
        return url

    @staticmethod
    def _title_slug(title: str) -> str:
        """Slugify a Shopify product title for use as a URL fragment.

        Strips trailing punctuation (WatchHouse titles end with ``.``),
        folds accented characters to ASCII, and joins words with ``-`` so a
        title like ``Nguvu Washed.`` becomes ``nguvu-washed``.
        """
        title = title.strip().rstrip(".")
        # Decompose accented chars (é -> e) and drop combining marks.
        title = unicodedata.normalize("NFKD", title)
        title = title.encode("ascii", "ignore").decode("ascii")
        title = title.lower()
        title = re.sub(r"[^a-z0-9]+", "-", title)
        return title.strip("-")

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from products.json, one per product.

        Each URL is suffixed with ``#<title-slug>`` so that when WatchHouse
        rotates the coffee under a stable handle (e.g. ``rituals-filter`` →
        ``Nguvu Washed.`` → next season a different bean), the fragment
        changes and the URL becomes distinct. The previous bean's URL then
        drops out of the catalog and the base scraper marks it out-of-stock,
        while the new bean is scraped as a fresh product.

        Args:
            store_url: URL of the products.json endpoint

        Returns:
            List of disambiguated product URLs (one per product)
        """
        products = await self._fetch_all_shopify_products(store_url)
        base_path = store_url.replace("/products.json", "")
        found_urls: list[str] = []

        for product in products:
            handle = product.get("handle")
            if not handle:
                continue

            if any(slug in handle for slug in self.exclude_slugs):
                logger.debug(f"Skipping excluded product slug: {handle}")
                continue

            title = product.get("title", "") or ""
            if not self.is_coffee_product_name(title):
                continue

            product_base_url = self.preprocess_product_url(f"{base_path}/products/{handle}")
            # ``product_base_url`` already has no fragment here because the
            # input has none; build the disambiguated URL from its base part.
            url_base = product_base_url.split("#", 1)[0]
            title_slug = self._title_slug(title)
            url = f"{url_base}#{title_slug}" if title_slug else url_base

            self._shopify_product_data[url] = product
            is_available = any(v.get("available", False) for v in product.get("variants", []))
            self._shopify_stock_status[url] = is_available

            if self.is_coffee_product_url(url_base):
                found_urls.append(url)

        return found_urls

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Keep only the ``div.main-product__grid`` section before AI extraction.

        WatchHouse product pages contain a lot of marketing chrome, related
        products, cross-sells, and footer content outside the actual product
        detail area. The product metadata we want the AI to extract lives in
        ``div.main-product__grid``, so we replace the body's contents with
        just that grid to avoid confusing the AI and wasting tokens. If the
        grid (or the body) is missing for some reason, fall back to leaving
        the soup untouched.
        """
        if not soup.body:
            logger.info("No <body> found; leaving soup untouched")
            return soup
        grid = soup.find("div", class_="main-product__grid")
        if grid is None:
            logger.info("No div.main-product__grid found; leaving soup untouched")
            return soup
        # Detach the grid so we can reinsert it into an emptied body.
        grid.extract()
        for child in list(soup.body.children):
            if hasattr(child, "decompose"):
                child.decompose()
        soup.body.append(grid)
        return soup
