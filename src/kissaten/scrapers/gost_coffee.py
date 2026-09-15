"""Gost Coffee Roasters scraper implementation with AI-powered extraction (Wix storefront)."""

import logging

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="gost-coffee",
    display_name="Gost Coffee Roasters",
    roaster_name="Gost Coffee Roasters",
    website="https://www.gostcoffee.com",
    description="Specialty coffee roaster and café based in New Lenox, Illinois, "
    "roasting single-origin coffees and blends alongside tea and brewing equipment.",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class GostCoffeeScraper(BaseScraper):
    """Scraper for Gost Coffee Roasters (gostcoffee.com) with AI-powered extraction.

    The site is a Wix storefront (verified via ``<meta name="generator"
    content="Wix.com Website Builder">``), so this follows the greytone_coffee.py
    model for product detail pages (``div[data-hook="product-page"]``).

    Discovery deviates from the greytone listing model: the ``/shop`` grid only
    renders the first 15 products server-side and does NOT support static
    ``?page=N`` pagination (verified: page 2+ return empty grids), so we use the
    static ``store-products-sitemap.xml`` for URL discovery instead, and probe
    each candidate's detail page JSON-LD for schema.org availability. Wix detail
    pages ARE fully server-rendered, so no Playwright is needed.
    """

    # Non-coffee slugs to exclude from the sitemap: teas, brewing equipment,
    # drinkware/merch, ready-to-drink cold brew, and instant "profile" sticks.
    _excluded_url_slugs = [
        # Teas / tisanes
        "tea",
        "assam",
        "chamomile",
        "earl-grey",
        "jasmine-petal-green",
        "tamayokucha",
        # Equipment / drinkware / merch
        "mug",
        "tumbler",
        "growler",
        "french-press",
        "chemex",
        "sibarist",
        "filter",
        "canister",
        "airscape",
        "coaster",
        "gost-coffee-pins",
        "tote-bags",
        "loop-rawhide",
        # Ready-to-drink / instant products
        "cold-brew",
        "gallon",
        "sticks",
        "profile-12",
    ]

    def __init__(self, api_key: str | None = None):
        """Initialize Gost Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Gost Coffee Roasters",
            base_url="https://www.gostcoffee.com",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the Wix store products sitemap URL.
        """
        return ["https://www.gostcoffee.com/store-products-sitemap.xml"]

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page and narrow product detail pages to the Wix product container.

        Wix product detail pages embed all useful content inside
        ``div[data-hook="product-page"]``. Narrowing the soup to that container
        strips nav, footer, JSON blobs, and unrelated markup before the HTML is
        sent to the AI extractor, which dramatically reduces token noise.

        Args:
            *args: Positional arguments forwarded to the base fetch_page.
            **kwargs: Keyword arguments forwarded to the base fetch_page.

        Returns:
            BeautifulSoup object (narrowed for product pages) or None if fetch failed.
        """
        soup = await super().fetch_page(*args, **kwargs)
        url = kwargs.get("url")
        if not url and len(args) > 0:
            url = args[0]
        # Only narrow product detail pages, leave listing/sitemap pages untouched
        if not url or "/product-page/" not in url:
            return soup
        if soup is None:
            return None
        product_el = soup.select("div[data-hook='product-page']")
        if len(product_el) == 1:
            logger.debug(f"Narrowed soup to div[data-hook='product-page'] for {url}")
            return product_el[0]
        logger.warning(f"Expected 1 div[data-hook='product-page'] for {url}, found {len(product_el)}")
        return soup

    async def _product_is_in_stock(self, product_url: str) -> bool:
        """Probe a Wix product detail page's JSON-LD availability.

        Wix detail pages are server-rendered and embed a schema.org ``Product``
        JSON-LD block with ``"availability":"https://schema.org/InStock"`` or
        ``.../OutOfStock``. On any fetch/parse failure we conservatively treat
        the product as in stock (a missed extraction is better than wrongly
        marking the catalogue out of stock).

        Args:
            product_url: Product detail URL

        Returns:
            True if the page does not explicitly mark the product out of stock.
        """
        soup = await self.fetch_page(product_url)
        if soup is None:
            logger.warning(f"Availability probe failed for {product_url}; assuming in stock")
            return True
        html = str(soup)
        return '"availability":"https://schema.org/OutOfStock"' not in html

    # Sold-out detection: Wix JSON-LD availability probe on each product detail
    # page. The sitemap carries no stock status and the /shop grid only renders
    # 15 of ~47 products with no static pagination, so card-level text detection
    # (greytone pattern) cannot see the whole catalogue. Each candidate's
    # server-rendered detail page is probed for
    # '"availability":"https://schema.org/OutOfStock"' and skipped BEFORE
    # coffee-URL filtering, so excluded products don't leak past the stock check.
    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract coffee product URLs from the Wix sitemap, filtering sold-out items.

        Args:
            store_url: URL of the store-products sitemap

        Returns:
            List of in-stock coffee product URLs
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            logger.error(f"Failed to fetch sitemap: {store_url}")
            return []

        candidates: list[str] = []
        seen: set[str] = set()
        for loc in soup.select("loc"):
            url = loc.get_text(strip=True)
            if not url:
                continue
            # Only product detail URLs
            if not self.is_coffee_product_url(url, required_path_patterns=["/product-page/"]):
                continue
            url_lower = url.lower()
            if any(slug in url_lower for slug in self._excluded_url_slugs):
                logger.debug(f"Excluding non-coffee product URL: {url}")
                continue
            if url not in seen:
                seen.add(url)
                candidates.append(url)

        logger.info(f"Found {len(candidates)} coffee candidate URLs from sitemap; probing availability")

        product_urls: list[str] = []
        for url in candidates:
            if await self._product_is_in_stock(url):
                product_urls.append(url)
            else:
                logger.debug(f"Skipping sold-out product: {url}")

        logger.info(f"Found {len(product_urls)} in-stock coffee product URLs from {store_url}")
        return product_urls

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

        Wix product pages carry no ``og:price:currency`` meta tag, so the base
        class's currency detection never fires and the registry default could
        silently fall back to GBP. Pin it here as a final guard.
        """
        bean.currency = "USD"
        return bean
