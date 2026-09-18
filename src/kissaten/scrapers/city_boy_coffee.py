"""City Boy Coffee scraper implementation with AI-powered extraction.

City Boy Coffee is a NYC specialty coffee roaster running WordPress +
WooCommerce. The site exposes the standard WooCommerce Store API at
``/wp-json/wc/store/v1/products`` which we use for product discovery and stock
status, and the product detail pages embed everything in a ``div.product``
container which we narrow to before AI extraction.

Note: the storefront also lists cafe drinks (americano, latte, ...) and a
coffee subscription; those are excluded by slug below.
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

API_PRODUCTS_URL = "https://cityboycoffee.com/wp-json/wc/store/v1/products"


@register_scraper(
    name="city-boy-coffee",
    display_name="City Boy Coffee",
    roaster_name="City Boy Coffee",
    website="https://cityboycoffee.com",
    description=(
        "NYC-based specialty coffee roaster offering single-origin beans, blends and decaf on a WooCommerce storefront."
    ),
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class CityBoyCoffeeScraper(BaseScraper):
    """Scraper for City Boy Coffee (cityboycoffee.com) with AI extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize City Boy Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="City Boy Coffee",
            base_url="https://cityboycoffee.com",
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
            translate_to_english=False,
        )

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page and narrow product detail pages to the WooCommerce container.

        The WooCommerce theme renders the full product UI (summary, tabs,
        gallery) inside ``div.product``. Narrowing to that container strips nav,
        footer, scripts and unrelated markup before the HTML is sent to the AI
        extractor.

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
            # Only narrow product detail pages (path starts with /product/),
            # leave the Store API JSON endpoints untouched.
            path = urlsplit(url or "").path
            if not path.startswith("/product/"):
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
        page = 1
        while page <= 5:  # safety cap: 20 products today, 100 per page
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
                product_urls.append(permalink)
            page += 1

        # Exclude cafe drinks, subscription, gift card and equipment — none of
        # them are coffee beans. Coffee products (including the Fermentation
        # Project pre-order when it is listed in stock) are kept.
        excluded_slugs = [
            "americano",
            "flat-white",
            "cortado",
            "cappuccino",
            "latte",
            "macchiato",
            "espresso",  # the cafe drink; bean products don't use this slug
            "extra-shot",
            "cascara-tea",  # cascara tea and tea gift set
            "coffee-scale",
            "gift-card",
            "sphere-coffee-club",  # subscription
        ]
        coffee_urls = [
            url
            for url in product_urls
            if self.is_coffee_product_url(url, required_path_patterns=["/product/"])
            and not any(ex in url.lower() for ex in excluded_slugs)
        ]
        logger.info(f"Found {len(coffee_urls)} in-stock coffee product URLs (page walk)")
        # Dedup in case overlapping Store API pages repeat a product.
        return list(dict.fromkeys(coffee_urls))

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Force the currency to USD as a final guard.

        The WooCommerce product pages have no og:price:currency meta tag, so
        the base class currency detection never fires and default_currency
        falls back to GBP. City Boy Coffee sells in USD.

        Args:
            bean: Extracted CoffeeBean object

        Returns:
            The bean with currency forced to USD
        """
        bean.currency = "USD"
        for option in bean.price_options or []:
            option.currency = "USD"
        return bean
