"""Love Letter Coffee scraper implementation with AI-powered extraction (Square Online).

Love Letter Coffee is a café in Amarillo, Texas on Square Online
(``love-letter-coffee.square.site``, `<meta name="generator" content="Square Online">`).
Like most Square Online storefronts the product cards and detail pages are
JS-rendered with no ``href`` anchors, so two proven Square patterns are
combined:

- Discovery: the static ``sitemap.xml`` (artificer.py pattern), which lists
  every product URL. The store API listing is unusable for this site: the
  whole-bean coffees are Square "hidden" products (in-store/wholesale retail
  bags) and Square's product listings only return menu items fulfilable at
  the pickup location, omitting them entirely.
- Detail: the Square Online store API (driftwood.py pattern) — the user/site
  ids came from the site's ``window.__BOOTSTRAP_STATE__`` and the runtime
  requests the page makes:

  - ``.../products/<id>`` (name, short_description, price, ``badges.out_of_stock``)
  - ``.../products/<id>/skus`` (per-variant name/price/``sold_out``)

  A compact soup is built from that JSON and fed to the AI extractor.

Quirks: this is a café catalogue (lattes, pastries, teas, merch) with a small
whole-bean lineup named after producers/farms (Chelchele, Habtamu, Fatima,
Finca San Antonio, Metapan, Ojo De Agua, San Carlos); drinks/food/merch are
excluded by slug. Most bean bags carry no descriptive text in Square at all
(``short_description`` is empty), so the AI extractor must work from the
product name alone for those.
"""

import asyncio
import logging

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="love-letter-coffee",
    display_name="Love Letter Coffee",
    roaster_name="Love Letter Coffee",
    website="https://love-letter-coffee.square.site",
    description="Amarillo, Texas café roasting single-origin whole-bean coffees "
    "alongside its espresso-bar menu and scratch bakery.",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class LoveLetterCoffeeScraper(BaseScraper):
    """Scraper for Love Letter Coffee (Square Online) with AI-powered extraction."""

    # Square Online store API base (user/site/location ids extracted from the
    # site's window.__BOOTSTRAP_STATE__ and its runtime store requests).
    _STORE_API_BASE = (
        "https://cdn5.editmysite.com/app/store/api/v28/editor/users/147725912/sites/480370494511930412"
        "/store-locations/L2CF09A82HWF9"
    )
    _PRODUCT_INCLUDES = "images,options,modifiers,category,media_files,fulfillment,discounts,subscriptions"

    # Non-coffee slugs to exclude: the café's espresso-bar menu, teas, bakery,
    # merch and wholesale items. The whole-bean coffees (Fatima, Habtamu,
    # Chelchele, Finca San Antonio, Metapan, Ojo De Agua, San Carlos) are NOT
    # excluded; any future sampler/tasting kit would be flagged for review
    # downstream instead of dropped.
    _excluded_url_slugs = [
        # Espresso-bar drinks
        "americano",
        "cappuccino",
        "cortado",
        "espresso",
        "latte",
        "macchiato",
        "cold-brew",
        "drip",
        "canned-",
        "texas-fog",
        "the-evelyn",
        "spritz",
        "mangonada",
        "hot-chocolate",
        "chocolate-milk",
        "milk",
        "water",
        "kids-",
        "traveler",
        # Teas
        "tea",
        "matcha",
        "chai",
        # Bakery / food
        "muffin",
        "croissant",
        "scone",
        "cookie",
        "brownie",
        "macaron",
        "pop-tart",
        "kolache",
        "danish",
        "morning-bun",
        "pie",
        "bar/",
        "krispies",
        "everything",
        # Merch / wholesale
        "shirt",
        "ringer",
        "wholesale",
    ]

    def __init__(self, api_key: str | None = None):
        """Initialize Love Letter Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Love Letter Coffee",
            base_url="https://love-letter-coffee.square.site",
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
        """Get store URLs to scrape.

        Square Online product cards render as JS buttons with no hrefs, so the
        static sitemap.xml is the discovery source (artificer.py pattern).

        Returns:
            List containing the sitemap URL.
        """
        return [f"{self.base_url}/sitemap.xml"]

    @staticmethod
    def _build_product_soup(product: dict, skus: list[dict]) -> BeautifulSoup:
        """Build a compact product soup from Square Online store API JSON.

        Args:
            product: Product object from ``.../products/<id>``
            skus: SKU objects from ``.../products/<id>/skus``

        Returns:
            BeautifulSoup object of the compact product markup.
        """
        parts: list[str] = ["<div>"]
        name = product.get("name")
        if name:
            parts.append(f"<h1>{name}</h1>")

        price = product.get("price") or {}
        low = price.get("low_formatted")
        high = price.get("high_formatted")
        if low and high and low != high:
            parts.append(f"<p>Price: {low} - {high}</p>")
        elif low or high:
            parts.append(f"<p>Price: {low or high}</p>")

        badges = product.get("badges") or {}
        availability = "Out of stock" if badges.get("out_of_stock") else "In stock"
        parts.append(f"<p>Availability: {availability}</p>")

        if skus:
            lines = ["Variants:"]
            for sku in skus:
                sku_name = sku.get("name") or "n/a"
                sku_price = (sku.get("price") or {}).get("current_formatted") or ""
                sku_stock = "Out of stock" if sku.get("sold_out") else "In stock"
                lines.append(f"- {sku_name} | Price: {sku_price} | Stock: {sku_stock}")
            parts.append(f"<pre>{'<br>'.join(lines)}</pre>")

        description = product.get("short_description")
        if description:
            parts.append(f"<div>{description}</div>")

        parts.append("</div>")
        return BeautifulSoup("".join(parts), "html.parser")

    async def _fetch_store_product_soup(self, product_url: str) -> BeautifulSoup | None:
        """Fetch a product's data from the Square Online store API as a compact soup.

        Args:
            product_url: Product detail URL (``.../product/<slug>/<id>``)

        Returns:
            Compact BeautifulSoup object, or None if the API fetch failed.
        """
        product_id = product_url.rstrip("/").split("/")[-1]
        if not product_id:
            return None
        api_url = f"{self._STORE_API_BASE}/products/{product_id}?include={self._PRODUCT_INCLUDES}"

        try:
            await asyncio.sleep(self.rate_limit_delay)
            response = await self.client.get(api_url)
            response.raise_for_status()
            product = response.json().get("data") or {}
            if not product:
                logger.warning(f"Empty store API payload for {product_url}")
                return None

            skus: list[dict] = []
            try:
                await asyncio.sleep(self.rate_limit_delay)
                skus_response = await self.client.get(f"{self._STORE_API_BASE}/products/{product_id}/skus")
                skus_response.raise_for_status()
                skus = skus_response.json().get("data") or []
            except Exception as e:
                logger.debug(f"SKU fetch failed for {product_url}: {e}")

            return self._build_product_soup(product, skus)

        except Exception as e:
            logger.warning(f"Store API fetch failed for {product_url}: {e}")
            return None

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page, using the store API for product detail pages.

        Square Online product pages are JS-rendered and expose no useful
        content to httpx, so for ``/product/`` URLs the page is rebuilt from
        the public store API instead. Any API failure falls back to the
        ordinary HTML fetch.

        Args:
            *args: Positional arguments forwarded to the base fetch_page.
            **kwargs: Keyword arguments forwarded to the base fetch_page.

        Returns:
            BeautifulSoup object or None if fetch failed.
        """
        url = kwargs.get("url")
        if not url and len(args) > 0:
            url = args[0]

        if url and "/product/" in url:
            product_soup = await self._fetch_store_product_soup(url)
            if product_soup is not None:
                return product_soup
            logger.warning(f"Falling back to HTML fetch for {url}")

        return await super().fetch_page(*args, **kwargs)

    # Sold-out detection: deferred to the store API detail payload
    # (``badges.out_of_stock`` / per-SKU ``sold_out``), which is rendered into
    # the compact soup as an explicit "Availability" line. The sitemap carries
    # no stock state, so nothing can be filtered at listing time here; the
    # base class's listing-failure guard still applies (a failed sitemap fetch
    # returns [] and is recorded as a failed store URL).
    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract coffee product URLs from the Square Online sitemap.

        Args:
            store_url: URL of the sitemap page

        Returns:
            List of coffee product URLs
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            logger.error(f"Failed to fetch sitemap: {store_url}")
            return []

        product_urls: list[str] = []
        for loc in soup.select("loc"):
            url = loc.get_text(strip=True)
            if not url:
                continue
            # Only product detail URLs
            if not self.is_coffee_product_url(url, required_path_patterns=["/product/"]):
                continue
            # Exclude café drinks / bakery / merch slugged in the sitemap
            url_lower = url.lower()
            if any(slug in url_lower for slug in self._excluded_url_slugs):
                logger.debug(f"Excluding non-coffee product URL: {url}")
                continue
            product_urls.append(url)

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_urls: list[str] = []
        for url in product_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        logger.info(f"Found {len(unique_urls)} coffee product URLs from sitemap")
        return unique_urls

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction.

        Args:
            product_urls: List of URLs for new products

        Returns:
            List of newly scraped CoffeeBean objects
        """
        if not product_urls:
            return []

        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=False,  # detail pages are rebuilt from the store API
            use_optimized_mode=False,
            translate_to_english=False,
        )

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Pin USD as the store currency.

        Square Online price strings carry no ISO currency code, so the base
        class's currency detection never fires and the registry default could
        silently fall back to GBP. Pin it here as a final guard (the store
        API's ``storeInfo.currency`` was verified as USD).
        """
        bean.currency = "USD"
        return bean
