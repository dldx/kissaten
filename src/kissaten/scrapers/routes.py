"""Routes Coffee scraper implementation with AI-powered extraction (WooCommerce).

Routes Coffee (routescoffee.co.uk) is an Oxford, UK roaster (Unit 5,
Fenchurch Court, Oxford OX4 6ZN) running WooCommerce with a Divi builder
theme. The public WooCommerce APIs are protected: the REST API
(``/wp-json/wc/v3/products``) returns 403 and the Store API
(``/wp-json/wc/store/v1/products``) returns an empty body, so we enumerate the
HTML catalogue instead. The whole-bean catalogue lives in the ``#coffee``
section of the homepage (``/#coffee``), rendered as WooCommerce ``li.product``
cards, with the Yoast ``product-sitemap.xml`` as a resilient second source.
Product detail URLs use the canonical ``/product/<slug>/`` form.
"""

import logging

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="routes",
    display_name="Routes Coffee",
    roaster_name="Routes Coffee",
    website="https://routescoffee.co.uk",
    description="Oxford, UK specialty coffee roaster (WooCommerce).",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class RoutesScraper(BaseScraper):
    """Scraper for Routes Coffee (routescoffee.co.uk) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize the Routes Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Routes Coffee",
            base_url="https://routescoffee.co.uk",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
        # The Store API is blocked and the Divi product pages expose no
        # og:price:currency meta tag, so the base currency detection never
        # fires. Routes Coffee prices in GBP (£); pin it up front.
        self.store_currency = "GBP"
        self._currency_detected = True

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page and narrow product detail pages to the ``div.product`` block.

        The Divi product template wraps all product info (name, price,
        tasting notes, roast, description) in a ``div.product`` block. Narrowing
        the soup to the largest such block strips nav, footer, and JS blobs
        (~1 MB down to ~25 KB) before the HTML reaches the AI extractor. Listing
        pages (homepage ``#coffee``) and the product sitemap are left untouched.

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
            # Only narrow product detail pages ("/product/..."); leave the
            # homepage catalogue and the sitemap untouched.
            if "/product/" not in (url or ""):
                return soup
            if soup is None:
                return None
            product_blocks = soup.select("div.product")
            if product_blocks:
                product_block = max(product_blocks, key=lambda block: len(str(block)))
                logger.debug(f"Narrowed soup to div.product for {url}")
                return product_block
            return soup
        except Exception as e:
            logger.error(f"Error fetching page: {e}")
            return None

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape (the #coffee catalogue + product sitemap)."""
        return [
            "https://routescoffee.co.uk/",
            "https://routescoffee.co.uk/product-sitemap.xml",
        ]

    def _get_excluded_url_patterns(self) -> list[str]:
        """Add Routes-specific non-bean patterns to the base exclusions.

        The ``14-x-coffee-pods-...`` product is a coffee-pod pack (not whole
        bean) and must be dropped; the base list already excludes capsules,
        gift cards, subscriptions, and equipment.
        """
        return super()._get_excluded_url_patterns() + ["coffee-pods", "pods"]

    async def _scrape_new_products(
        self, product_urls: list[str], use_optimized_mode: bool = False
    ) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction.

        Args:
            product_urls: List of URLs for new products
            use_optimized_mode: Whether to use optimized (visual) extraction mode

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
            use_optimized_mode=use_optimized_mode,
        )

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        # No og:price:currency meta on the Divi product pages, so force GBP.
        bean.currency = "GBP"
        return bean

    # Sold-out detection: WooCommerce adds the `outofstock` class to the
    # li.product card when a product is unavailable, so we skip any card whose
    # class list contains `outofstock`. Runs before is_coffee_product_url.
    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract coffee product URLs from a store page.

        Handles both the HTML catalogue (the homepage ``#coffee`` section with
        WooCommerce ``li.product`` cards) and the Yoast product sitemap
        (``<loc>`` entries for ``/product/<slug>/`` URLs).

        Args:
            store_url: URL of the store/listing page

        Returns:
            List of coffee product URLs
        """
        soup = await self.fetch_page(store_url)
        if soup is None:
            return []

        product_urls: list[str] = []

        # Sitemap branch: Yoast emits a flat <loc> list of product URLs.
        if store_url.rstrip("/").endswith(".xml"):
            for loc in soup.find_all("loc"):
                href = loc.get_text(strip=True)
                if not href or not isinstance(href, str):
                    continue
                full_url = self.resolve_url(href)
                if self.is_coffee_product_url(full_url, required_path_patterns=["/product/"]):
                    if full_url not in product_urls:
                        product_urls.append(full_url)
            logger.info(f"Found {len(product_urls)} coffee product URLs from sitemap {store_url}")
            return product_urls

        # HTML branch: the whole-bean catalogue is the #coffee section on the
        # homepage; fall back to the full soup if the section id ever changes.
        section = soup.find(id="coffee")
        container = section if section is not None else soup

        for card in container.select("li.product"):
            # Skip sold-out cards (WooCommerce `outofstock` class marker).
            if "outofstock" in (card.get("class") or []):
                continue
            link = card.select_one('a[href*="/product/"]')
            if not link:
                continue
            href = link.get("href")
            if not href or not isinstance(href, str):
                continue
            full_url = self.resolve_url(href)
            if self.is_coffee_product_url(full_url, required_path_patterns=["/product/"]):
                if full_url not in product_urls:
                    product_urls.append(full_url)

        logger.info(f"Found {len(product_urls)} coffee product URLs from {store_url}")
        return product_urls
