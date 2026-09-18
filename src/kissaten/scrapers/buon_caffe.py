"""Buon Caffe (步昂咖啡) scraper implementation with AI-powered extraction.

Buon Caffe is a Taiwanese specialty coffee roaster running WordPress +
WooCommerce (zh-TW storefront). The site exposes the standard WooCommerce
Store API at ``/wp-json/wc/store/v1/products`` which we use for product
discovery and stock status, and the product detail pages embed everything in a
``div.product`` container which we narrow to before AI extraction.
"""

import json
import logging
from urllib.parse import urlsplit

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)

API_PRODUCTS_URL = "https://buoncaffe.com.tw/wp-json/wc/store/v1/products"


@register_scraper(
    name="buon-caffe",
    display_name="Buon Caffe",
    roaster_name="Buon Caffe",
    website="https://buoncaffe.com.tw",
    description=(
        "Taiwanese specialty coffee roaster (步昂咖啡) based in Taipei, offering "
        "freshly roasted single-origin beans and blends."
    ),
    requires_api_key=True,
    currency="TWD",
    country="Taiwan",
    status="experimental",
)
class BuonCaffeScraper(BaseScraper):
    """Scraper for Buon Caffe (buoncaffe.com.tw) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Buon Caffe scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Buon Caffe",
            base_url="https://buoncaffe.com.tw",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get the WooCommerce Store API products endpoint.

        Pagination is handled inside _extract_product_urls_from_store, which
        walks ``?page=N`` until an empty page is returned.
        """
        return [f"{API_PRODUCTS_URL}?per_page=100&page=1"]

    async def _fetch_products_page(self, page: int) -> list[dict] | None:
        """Fetch one page of the WooCommerce Store API products endpoint.

        Args:
            page: 1-indexed page number

        Returns:
            List of product dicts, or None if the fetch/parse failed.
        """
        url = f"{API_PRODUCTS_URL}?per_page=100&page={page}"
        soup = await self.fetch_page(url)
        if soup is None:
            return None

        try:
            data = json.loads(soup.get_text())
        except (json.JSONDecodeError, ValueError):
            logger.warning(f"Could not parse Store API response as JSON: {url}")
            return None

        if not isinstance(data, list):
            logger.warning(f"Unexpected Store API response (not a list): {url}")
            return None
        return data

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
            translate_to_english=True,  # zh-TW storefront — translate to English
        )

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page and narrow product detail pages to the WooCommerce container.

        The WooCommerce theme renders the full product UI (summary, tabs, gallery)
        inside ``div.product``; the surrounding page is >1.5 MB of nav, scripts
        and JSON blobs. Narrowing to that container cuts the HTML sent to the AI
        extractor by ~98% with zero information loss.

        Args:
            *args: Positional arguments forwarded to the base fetch_page.
            **kwargs: Keyword arguments forwarded to the base fetch_page.

        Returns:
            BeautifulSoup object (narrowed for product pages) or None if fetch failed.
        """
        try:
            soup = await super().fetch_page(*args, **kwargs)
            url = kwargs.get("url")
            if not url and len(args) > 0:
                url = args[0]
            # Only narrow product detail pages (path starts with /products/),
            # leave the Store API JSON endpoints untouched.
            path = urlsplit(url or "").path
            if not path.startswith("/products/"):
                return soup
            if soup is None:
                return None
            product_el = soup.select("div.product")
            if len(product_el) == 1:
                logger.debug(f"Narrowed soup to div.product for {url}")
                return product_el[0]
            logger.warning(f"Expected 1 div.product for {url}, found {len(product_el)}")
            return soup
        except Exception as e:
            logger.error(f"Error fetching page {url if 'url' in dir() else '?'}: {e}")
            return None

    # Sold-out detection: WooCommerce Store API `is_in_stock` field. The Store
    # API exposes per-product stock status directly in the JSON listing, which
    # is the cheapest possible check — no HTML card parsing needed. Products
    # with is_in_stock=False are skipped before is_coffee_product_url
    # filtering, so excluded products don't leak past the stock check.
    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract in-stock product URLs from the WooCommerce Store API.

        Walks all ``?page=N`` pages until an empty page is returned. If the
        first page fails to load, returns [] so the base class records the
        listing as failed and skips out-of-stock diffjson updates.

        Args:
            store_url: The Store API products URL (ignored in favour of the
                canonical endpoint with pagination)

        Returns:
            List of in-stock coffee product URLs
        """
        product_urls: list[str] = []
        seen: set[str] = set()
        page = 1
        while page <= 10:  # safety cap: 301 products / 100 per page = 4 pages today
            data = await self._fetch_products_page(page)
            if data is None:
                if page == 1:
                    logger.error("Failed to fetch first Store API page; aborting listing extraction")
                    return []
                break
            if not data:
                break
            for product in data:
                # Sold-out detection: skip products flagged out of stock
                if not product.get("is_in_stock", True):
                    logger.debug(f"Skipping sold-out product: {product.get('permalink')}")
                    continue
                permalink = product.get("permalink")
                if not permalink or not isinstance(permalink, str):
                    continue
                if permalink in seen:
                    continue
                seen.add(permalink)
                product_urls.append(permalink)
            page += 1

        # Exclude non-coffee items: green/wholesale beans, drip bags (濾掛),
        # gift boxes (禮盒) and equipment. The James Hoffmann Fermentation
        # Project kits (e.g. /products/203180/, /products/the-fermentation-project/)
        # are NOT excluded — they are extracted and flagged as tasting kits
        # downstream.
        excluded_slugs = [
            "greenbeans",  # green bean private/wholesale listings (生豆賣場)
            "green-beans-wholesale",
            "giftbox",  # gift boxes (禮盒)
            "gift-box",
            "drip",  # drip bags (濾掛): *dripbag*, drip10g-classic, *drip*, 15gdrips
            "equipment",
            "merch",
        ]
        coffee_urls = [
            url
            for url in product_urls
            if self.is_coffee_product_url(url, required_path_patterns=["/products/"])
            and not any(ex in url.lower() for ex in excluded_slugs)
        ]
        logger.info(f"Found {len(coffee_urls)} in-stock coffee product URLs (page walk)")
        return coffee_urls

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Force the currency to TWD.

        The WooCommerce product pages have no og:price:currency meta tag, so
        the base class currency detection never fires and default_currency
        falls back to GBP. Buon Caffe sells in New Taiwan dollars.

        Args:
            bean: Extracted CoffeeBean object

        Returns:
            The bean with currency forced to TWD
        """
        bean.currency = "TWD"
        for option in bean.price_options or []:
            option.currency = "TWD"
        return bean
