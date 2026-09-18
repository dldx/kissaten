"""Roosevelt Coffeehouse scraper implementation with AI-powered extraction (WooCommerce).

Roosevelt Coffeehouse is a nonprofit coffeehouse/roaster in Columbus, Ohio
("Good Coffee for Good"). The main site is ``rooseveltcoffee.org`` (WordPress
+ Site Kit + the Give donation plugin), but the WooCommerce shop itself is
served from the ``roosevelt.coffee`` domain (linked from the .org `/shop/`
page). Product detail pages are server-rendered, but the public WooCommerce
Store API (``/wp-json/wc/store/v1/products``) exposes complete structured
product data (name, description with origin/process notes, minor-unit prices,
weight/grind variations, stock status) — so the scraper uses the Store API for
both listing and detail instead of parsing HTML (lantern.py pattern):

- Listing: ``.../products?per_page=100&page=N`` (name, permalink, categories,
  ``is_in_stock``). Coffee products carry NO category, while merch lives in
  ``Merchandise``, gift cards in ``Gifts`` and the coffee subscription in
  ``Bundles`` — nonprofit donation pages are not WooCommerce products at all.
- Detail: ``.../products?slug=<slug>`` returns the same product shape, from
  which a compact soup is built and fed to the AI extractor. This avoids one
  heavyweight (240+ KB, Avada/Elementor) HTML fetch per product.

Limitations: product pages only expose the same text the Store API carries
(no extra carousel/accordion content), so nothing is lost by using the API.
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
    name="roosevelt-coffeehouse",
    display_name="Roosevelt Coffeehouse",
    roaster_name="Roosevelt Coffeehouse",
    website="https://rooseveltcoffee.org",
    description="Nonprofit coffeehouse and roaster in Columbus, Ohio funding clean-water, "
    "education and hunger-fighting projects through coffee sales.",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class RooseveltCoffeehouseScraper(BaseScraper):
    """Scraper for Roosevelt Coffeehouse using the WooCommerce Store API."""

    # WooCommerce Store API endpoint on the shop domain (public, no auth).
    _STORE_API_URL = "https://roosevelt.coffee/wp-json/wc/store/v1/products"
    _LISTING_QUERY = "per_page=100&page={page}"
    _max_listing_pages = 10

    # Category names that mark non-coffee products (merch, gift cards, and the
    # Franks Choice coffee subscription). Coffee beans carry no category at all,
    # so any product in one of these categories is skipped. Donations made via
    # the Give plugin are not WooCommerce products and never appear here.
    _excluded_categories = {"Merchandise", "Gifts", "Bundles"}

    # Belt-and-braces slug guard in case categories change. Sampler/taster
    # packs are NOT excluded — they are flagged is_tasting_kit/requires_review
    # downstream.
    _excluded_url_slugs = [
        "subscription",
        "gift-card",
        "gift",
        "t-shirt",
        "tshirt",
        "hat",
        "mug",
        "tumbler",
        "poster",
        "journal",
        "hoodie",
        "sticker",
    ]

    def __init__(self, api_key: str | None = None):
        """Initialize Roosevelt Coffeehouse scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Roosevelt Coffeehouse",
            base_url="https://roosevelt.coffee",
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
        """Get store URLs to scrape (WooCommerce Store API product listing)."""
        return [f"{self._STORE_API_URL}?{self._LISTING_QUERY.format(page=1)}"]

    @staticmethod
    def _format_price(amount: str | None, prices: dict) -> str:
        """Format a WooCommerce minor-unit amount using the payload's currency block."""
        if amount is None:
            return ""
        try:
            minor_unit = int(prices.get("currency_minor_unit") or 2)
            value = int(amount) / (10**minor_unit)
        except (TypeError, ValueError):
            return amount
        prefix = prices.get("currency_prefix") or ""
        suffix = prices.get("currency_suffix") or ""
        decimal = prices.get("currency_decimal_separator") or "."
        return f"{prefix}{value:.{minor_unit}f}".replace(".", decimal) + suffix

    @classmethod
    def _build_product_soup(cls, product: dict) -> BeautifulSoup:
        """Build a compact product soup from a WooCommerce Store API product.

        Args:
            product: Product object from ``.../products?slug=<slug>``

        Returns:
            BeautifulSoup object of the compact product markup.
        """
        prices = product.get("prices") or {}
        parts: list[str] = ["<div>"]

        name = product.get("name")
        if name:
            parts.append(f"<h1>{name}</h1>")

        price_range = prices.get("price_range") or {}
        low = cls._format_price(price_range.get("min_amount"), prices)
        high = cls._format_price(price_range.get("max_amount"), prices)
        if low and high and low != high:
            parts.append(f"<p>Price: {low} - {high}</p>")
        elif low or high:
            parts.append(f"<p>Price: {low or high}</p>")

        availability = "In stock" if product.get("is_in_stock") else "Out of stock"
        parts.append(f"<p>Availability: {availability}</p>")

        # Variations carry Weight × Grind attribute pairs; collapse them into
        # the unique values per attribute so the AI extractor sees the
        # available sizes without duplicated lines.
        attribute_values: dict[str, list[str]] = {}
        for variation in product.get("variations") or []:
            for attr in variation.get("attributes") or []:
                attr_name = attr.get("name")
                value = attr.get("value")
                if attr_name and value:
                    seen = attribute_values.setdefault(attr_name, [])
                    if value not in seen:
                        seen.append(value)
        if attribute_values:
            lines = ["Variants:"]
            for attr_name, values in attribute_values.items():
                lines.append(f"- {attr_name}: {', '.join(values)}")
            parts.append(f"<pre>{'<br>'.join(lines)}</pre>")

        description = product.get("description") or product.get("short_description")
        if description:
            parts.append(f"<div>{description}</div>")

        parts.append("</div>")
        return BeautifulSoup("".join(parts), "html.parser")

    async def _fetch_store_product_soup(self, product_url: str) -> BeautifulSoup | None:
        """Fetch a product's data from the WooCommerce Store API as a compact soup.

        Args:
            product_url: Product detail URL (``https://roosevelt.coffee/product/<slug>/``)

        Returns:
            Compact BeautifulSoup object, or None if the API fetch failed.
        """
        slug = product_url.rstrip("/").split("/")[-1]
        if not slug:
            return None
        api_url = f"{self._STORE_API_URL}?slug={slug}"

        try:
            await asyncio.sleep(self.rate_limit_delay)
            response = await self.client.get(api_url)
            response.raise_for_status()
            items = response.json() or []
            if not items:
                logger.warning(f"Empty store API payload for {product_url}")
                return None
            return self._build_product_soup(items[0])
        except Exception as e:
            logger.warning(f"Store API fetch failed for {product_url}: {e}")
            return None

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page, using the Store API for product detail pages.

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

    # Sold-out detection: WooCommerce Store API ``is_in_stock`` flag.
    # The API listing carries explicit per-product stock state, so sold-out
    # items are skipped BEFORE coffee-URL filtering, and the base class's
    # listing-failure guard still applies (a failed API fetch returns [] and
    # is recorded as a failed store URL).
    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract coffee product URLs from the WooCommerce Store API listing.

        Args:
            store_url: URL of the Store API products listing (page 1)

        Returns:
            List of in-stock coffee product URLs
        """
        product_urls: list[str] = []

        for page in range(1, self._max_listing_pages + 1):
            listing_url = f"{self._STORE_API_URL}?{self._LISTING_QUERY.format(page=page)}"
            try:
                response = await self.client.get(listing_url)
                response.raise_for_status()
                items = response.json() or []
            except Exception as e:
                logger.error(f"Failed to fetch store API listing {listing_url}: {e}")
                # A failed listing fetch must return [] so the base class
                # records the store URL as failed and skips OOS updates.
                return []

            if not items:
                break

            for item in items:
                # Skip sold-out products before URL-pattern filtering
                if not item.get("is_in_stock", True):
                    logger.debug(f"Skipping sold-out product: {item.get('name')}")
                    continue

                # Coffee beans carry no category; merch/gifts/subscription do.
                category_names = {c.get("name", "") for c in item.get("categories") or []}
                if category_names & self._excluded_categories:
                    logger.debug(f"Skipping non-coffee product: {item.get('name')} ({category_names})")
                    continue

                url = item.get("permalink") or ""
                if not url:
                    continue

                url_lower = url.lower()
                if any(slug in url_lower for slug in self._excluded_url_slugs):
                    logger.debug(f"Excluding non-coffee product URL: {url}")
                    continue
                if not self.is_coffee_product_url(url, required_path_patterns=["/product/"]):
                    continue

                product_urls.append(url)

        # Deduplicate while preserving order
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

        The base class's display-name currency lookup can silently fall back
        to GBP, so pin the verified home currency (USD, confirmed via the
        Store API ``currency_code`` field) here as a final guard.
        """
        bean.currency = "USD"
        return bean
