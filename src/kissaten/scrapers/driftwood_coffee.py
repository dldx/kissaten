"""Driftwood Coffee scraper implementation with AI-powered extraction (Square Online)."""

import asyncio
import logging

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="driftwood-coffee",
    display_name="Driftwood Coffee",
    roaster_name="Driftwood Coffee",
    website="https://www.driftwood.coffee",
    description="Specialty coffee roaster and café based in Corpus Christi, Texas, "
    "serving house-roasted single origins and blends.",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class DriftwoodCoffeeScraper(BaseScraper):
    """Scraper for Driftwood Coffee (driftwood.coffee) with AI-powered extraction.

    The site is a Square Online (Weebly) storefront — product pages are
    JS-rendered and do NOT render ``div.product-detail-page`` in headless
    Chromium (verified: only a shell renders, and ``?cs=true&cst=custom``
    intermittently redirects to the cart). However, Square Online exposes a
    public store API that returns complete product data as JSON:

    - Listing: ``.../products?page=N&per_page=100`` (name, site_link, price
      range, ``badges.out_of_stock``)
    - Detail: ``.../products/<id>`` (name, short_description, price, inventory)
    - Variants: ``.../products/<id>/skus`` (per-variant name/price/``sold_out``)

    This follows (and improves on) the artificer.py Square Online model: the
    sitemap is replaced by the store API listing, which additionally carries
    price and stock status, and the (JS-only) product detail HTML is replaced
    by a compact soup built from the API JSON.
    """

    # Square Online store API base (user/site ids extracted from the site's
    # window.__BOOTSTRAP_STATE__ / editmysite CDN URLs).
    _STORE_API_BASE = "https://cdn5.editmysite.com/app/store/api/v28/editor/users/150602263/sites/172140773665606663"
    _LISTING_QUERY = "page={page}&per_page=100&sort_by=popularity_score&visibilities%5B%5D=visible"
    _max_listing_pages = 10

    # Non-coffee slugs to exclude: café drinks, food, merch, wholesale bag
    # variants ("-ws-"/"wholesale"/"ws-colombia"), and subscriptions.
    # The Fermentation Project tasting kit and 2oz sample bags are NOT excluded
    # (tasting-kit flagging is automatic downstream).
    _excluded_url_slugs = [
        # Café drinks
        "americano",
        "cappuccino",
        "cortado",
        "espresso",
        "flat-white",
        "latte",
        "macchiato",
        "iced-",
        "shaken",
        "pour-over",
        "drip",
        "cold-brew",
        "gallon",
        "chai",
        "matcha",
        "tea",
        "hot-chocolate",
        "lemonade",
        "maple",
        # Food
        "muffin",
        "croissant",
        "focaccia",
        # Merch / retail extras
        "burlap",
        "coffee-carrier",
        "sticker",
        "straw",
        "t-shirt",
        "syrup",
        # Wholesale bag variants
        "wholesale",
        "-ws-",
        "ws-colombia",
        # Subscriptions / special orders
        "subscription",
        "pre-paid",
        "special-bulk-order",
        "rush-order",
    ]

    def __init__(self, api_key: str | None = None):
        """Initialize Driftwood Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Driftwood Coffee",
            base_url="https://www.driftwood.coffee",
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

        Returns:
            List containing the Square Online store API products listing URL.
        """
        return [f"{self._STORE_API_BASE}/products?{self._LISTING_QUERY.format(page=1)}"]

    @staticmethod
    def _build_product_soup(product: dict, skus: list[dict]) -> BeautifulSoup:
        """Build a compact product soup from Square Online store API JSON.

        The rendered product page is JS-only, so the AI extractor is fed this
        structured soup instead: name, price range, availability, per-SKU
        variants (size/weight), and the full description.

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
        api_url = f"{self._STORE_API_BASE}/products/{product_id}"

        try:
            await asyncio.sleep(self.rate_limit_delay)
            response = await self.client.get(api_url)
            response.raise_for_status()
            product = (response.json().get("data")) or {}
            if not product:
                logger.warning(f"Empty store API payload for {product_url}")
                return None

            skus: list[dict] = []
            try:
                await asyncio.sleep(self.rate_limit_delay)
                skus_response = await self.client.get(f"{api_url}/skus")
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

        Product detail pages on Square Online are JS-rendered and never expose
        their content to httpx or headless Chromium, so for ``/product/`` URLs
        we build the page from the public store API instead. Any API failure
        falls back to the ordinary HTML fetch (which still yields the
        server-rendered og:title/og:description meta tags).

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

    # Sold-out detection: Square Online store API ``badges.out_of_stock`` flag.
    # The API listing carries explicit per-product stock badges (unlike the
    # static sitemap), so sold-out items are skipped BEFORE coffee-URL
    # filtering, and the base class's listing-failure guard still applies
    # (a failed API fetch returns [] and is recorded as a failed store URL).
    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract coffee product URLs from the Square Online store API listing.

        Args:
            store_url: URL of the store API products listing

        Returns:
            List of in-stock coffee product URLs
        """
        product_urls: list[str] = []
        page = 1
        total_pages = 1

        while page <= min(total_pages, self._max_listing_pages):
            listing_url = (
                store_url
                if page == 1 and "page=1" in store_url
                else f"{self._STORE_API_BASE}/products?{self._LISTING_QUERY.format(page=page)}"
            )
            try:
                response = await self.client.get(listing_url)
                response.raise_for_status()
                payload = response.json()
            except Exception as e:
                logger.error(f"Failed to fetch store API listing {listing_url}: {e}")
                return []

            items = payload.get("data") or []
            pagination = (payload.get("meta") or {}).get("pagination") or {}
            try:
                total_pages = int(pagination.get("total_pages") or 1)
            except (TypeError, ValueError):
                total_pages = 1

            for item in items:
                # Skip sold-out products before URL-pattern filtering
                if (item.get("badges") or {}).get("out_of_stock"):
                    logger.debug(f"Skipping sold-out product: {item.get('name')}")
                    continue

                site_link = item.get("site_link") or ""
                if not site_link:
                    continue
                url = f"{self.base_url}/{site_link.lstrip('/')}"

                # Exclude non-coffee products (drinks, food, merch, wholesale)
                url_lower = url.lower()
                if any(slug in url_lower for slug in self._excluded_url_slugs):
                    logger.debug(f"Excluding non-coffee product URL: {url}")
                    continue
                if not self.is_coffee_product_url(url, required_path_patterns=["/product/"]):
                    continue

                product_urls.append(url)

            page += 1

        # Deduplicate while preserving order (slugs can repeat with different ids)
        unique_urls = list(dict.fromkeys(product_urls))
        logger.info(f"Found {len(unique_urls)} in-stock coffee product URLs from {store_url}")
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
            use_playwright=False,
            use_optimized_mode=False,
            translate_to_english=False,
        )

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Pin USD as the store currency.

        Square Online price strings carry no ISO currency code, so the base
        class's currency detection never fires and the registry default could
        silently fall back to GBP. Pin it here as a final guard.
        """
        bean.currency = "USD"
        return bean
