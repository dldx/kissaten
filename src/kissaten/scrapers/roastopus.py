"""Roastopus scraper implementation with AI-powered extraction (custom Laravel + Vue storefront).

Roastopus (roastopus.com) is a specialty coffee roaster in Hungary. The site is a
custom Laravel + Vue storefront with server-rendered product data (no Shopify,
no WooCommerce).

Platform notes from curl-first discovery (2026-09):
- Coffee categories: ``/hu/termekeink/kaveink-espresso`` (14 products) and
  ``/hu/termekeink/kaveink-filter`` (8 products). ``/hu/termekeink`` itself 404s.
- Category pages embed a ``ItemList`` JSON-LD block naming every product URL,
  which is the discovery source (product cards carry no anchors in the HTML).
- Product pages are server-rendered: the ``section.product-datasheet`` container
  holds the datasheet (country, region, station, producer, process, varietals,
  altitude, tasting notes, roast profile) in Hungarian, and the
  ``<roastopus-product-price :products="[...]">`` Vue component carries the
  per-size prices (``price_plus_vat`` in Ft). Prices are *not* visible text, so
  ``fetch_page`` injects them into the narrowed soup.
- Stock status comes from the ``Product`` JSON-LD ``offers[].availability``
  (``InStock`` / ``OutOfStock``); the category ItemList has no stock data, so
  discovery checks each product page once and caches the soup for the extraction
  pass.
- Catalogue language is Hungarian -> ``translate_to_english=True``; currency HUF.
"""

import html as html_lib
import json
import logging
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="roastopus",
    display_name="Roastopus",
    roaster_name="Roastopus",
    website="https://roastopus.com",
    description="Specialty coffee roaster in Hungary (custom Laravel + Vue storefront).",
    requires_api_key=True,
    currency="HUF",
    country="Hungary",
    status="experimental",
)
class RoastopusScraper(BaseScraper):
    """Scraper for Roastopus (roastopus.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize the Roastopus scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Roastopus",
            base_url="https://roastopus.com",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = None
        try:
            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
        except ValueError:
            logger.warning("Google API key not configured. AI extraction will not be available.")

        # Raw product-page soups fetched during discovery, reused by the
        # extraction pass so each product page is downloaded only once.
        self._raw_soup_by_url: dict[str, BeautifulSoup] = {}

    async def get_store_urls(self) -> list[str]:
        """Get the two coffee category URLs.

        Returns:
            List of espresso and filter category URLs.
        """
        return [
            "https://roastopus.com/hu/termekeink/kaveink-espresso",
            "https://roastopus.com/hu/termekeink/kaveink-filter",
        ]

    @staticmethod
    def _is_product_url(url: str) -> bool:
        """Return True for product detail URLs (category URLs are excluded).

        Category paths have three segments (``/hu/termekeink/kaveink-espresso``)
        while product detail URLs add a product slug segment.
        """
        parts = [part for part in urlparse(url or "").path.strip("/").split("/") if part]
        return len(parts) >= 4 and "termekeink" in parts and any(part.startswith("kaveink-") for part in parts)

    @staticmethod
    def _extract_item_list_urls(soup: BeautifulSoup | Tag) -> list[str]:
        """Extract product URLs from the category page's ItemList JSON-LD.

        Args:
            soup: Category page soup.

        Returns:
            Product detail URLs in listing order.
        """
        urls: list[str] = []
        for script in soup.find_all("script", type="application/ld+json"):
            blob = script.string or script.get_text() or ""
            try:
                data = json.loads(blob)
            except (ValueError, json.JSONDecodeError):
                continue
            if not isinstance(data, dict) or data.get("@type") != "ItemList":
                continue
            for item in data.get("itemListElement") or []:
                url = item.get("url")
                if url and url not in urls:
                    urls.append(url)
        return urls

    @staticmethod
    def _extract_availability(soup: BeautifulSoup | Tag) -> str | None:
        """Read the stock status from the Product JSON-LD offers.

        Args:
            soup: Full (un-narrowed) product page soup.

        Returns:
            Availability token such as "InStock"/"OutOfStock", or None when unknown.
        """
        for script in soup.find_all("script", type="application/ld+json"):
            blob = script.string or script.get_text() or ""
            try:
                data = json.loads(blob)
            except (ValueError, json.JSONDecodeError):
                continue
            if not isinstance(data, dict) or data.get("@type") != "Product":
                continue
            offers = data.get("offers") or []
            if isinstance(offers, dict):
                offers = [offers]
            for offer in offers:
                availability = offer.get("availability")
                if availability:
                    return str(availability).rsplit("/", 1)[-1]
        return None

    @classmethod
    def _extract_price_lines(cls, soup: BeautifulSoup | Tag) -> list[str]:
        """Extract per-size price lines from the roastopus-product-price Vue component.

        Args:
            soup: Full (un-narrowed) product page soup.

        Returns:
            Lines such as "- Price: 4390 Ft".
        """
        component = soup.select_one("roastopus-product-price")
        raw = component.get(":products") if component else None
        if not raw:
            return []

        try:
            products = json.loads(html_lib.unescape(raw))
        except (ValueError, json.JSONDecodeError) as e:
            logger.debug(f"Could not parse roastopus-product-price payload: {e}")
            return []

        lines = []
        for product in products or []:
            price = product.get("price") or {}
            amount = price.get("price_plus_vat") or price.get("price")
            if not amount:
                continue
            currency = price.get("currency") or "Ft"
            lines.append(f"- Price: {amount} {currency}")
        return lines

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page, narrowing product detail pages to the datasheet container.

        The raw product soup (with prices and JSON-LD) is cached during discovery
        so the extraction pass reuses it. The narrowed soup keeps the Hungarian
        datasheet plus injected price/availability lines.

        Args:
            *args: Positional arguments forwarded to the base fetch_page.
            **kwargs: Keyword arguments forwarded to the base fetch_page.

        Returns:
            BeautifulSoup object (narrowed for product pages) or None if the fetch failed.
        """
        url = kwargs.get("url") or (args[0] if args else "")
        if not url or not self._is_product_url(url):
            return await super().fetch_page(*args, **kwargs)

        soup = self._raw_soup_by_url.get(url)
        if soup is None:
            soup = await super().fetch_page(url)
            if soup is None:
                return None
            self._raw_soup_by_url[url] = soup

        section = soup.select_one("section.product-datasheet")
        if section is None:
            logger.warning(f"Could not find section.product-datasheet for {url}")
            return soup

        price_lines = self._extract_price_lines(soup)
        availability = self._extract_availability(soup)
        if price_lines or availability:
            extra = BeautifulSoup("<div></div>", "lxml").div
            if price_lines:
                extra.append(BeautifulSoup("<h2>Prices</h2>", "lxml").h2)
                for line in price_lines:
                    extra.append(BeautifulSoup(f"<p>{line}</p>", "lxml").p)
            if availability:
                extra.append(BeautifulSoup(f"<p>Availability: {availability}</p>", "lxml").p)
            section.append(extra)

        logger.debug(f"Narrowed soup to section.product-datasheet for {url}")
        return section

    # Sold-out detection: Product JSON-LD offers[].availability ("OutOfStock").
    # The category ItemList carries no stock data, so each product page is
    # checked once here (cached for the extraction pass); out-of-stock products
    # are left out of the current URL list so the base class records them as
    # out-of-stock updates instead of in-stock refreshes.
    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract in-stock coffee product URLs from a category page.

        Args:
            store_url: Category page URL.

        Returns:
            List of in-stock product URLs.
        """
        soup = await super().fetch_page(store_url)
        if not soup:
            return []

        candidate_urls = [
            url
            for url in self._extract_item_list_urls(soup)
            if self.is_coffee_product_url(url, required_path_patterns=["/termekeink/"])
        ]

        product_urls: list[str] = []
        for url in candidate_urls:
            product_soup = await super().fetch_page(url)
            if product_soup is not None:
                self._raw_soup_by_url[url] = product_soup

            availability = self._extract_availability(product_soup) if product_soup else None
            if availability and "outofstock" in availability.lower().replace(" ", ""):
                logger.debug(f"Skipping sold-out product: {url}")
                continue

            product_urls.append(url)

        logger.info(f"Found {len(product_urls)} in-stock coffee product URLs from {store_url}")
        return product_urls

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
            # Hungarian-language catalogue.
            translate_to_english=True,
        )

    def postprocess_review_flags(self, bean: CoffeeBean, url: str) -> CoffeeBean:
        """Flag the Fermentation Project / mini tasting pack products for review."""
        haystack = f"{url} {getattr(bean, 'name', '') or ''}".lower()
        if "fermentation-project" in haystack or "minicsomag" in haystack:
            bean.is_tasting_kit = True
        return bean

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Pin the store currency (the registry lookup by display name can fall back to GBP)."""
        bean.currency = "HUF"
        return bean
