"""Greytone Coffee scraper implementation with AI-powered extraction (Wix storefront)."""

import logging

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="greytone-coffee",
    display_name="Greytone Coffee",
    roaster_name="Greytone Coffee",
    website="https://www.greytonecoffee.co.uk",
    description="Specialty coffee roaster based in Bristol, United Kingdom, born with a belief in letting coffee speak for itself.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class GreytoneCoffeeScraper(BaseScraper):
    """Scraper for Greytone Coffee (greytonecoffee.co.uk) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Greytone Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Greytone Coffee",
            base_url="https://www.greytonecoffee.co.uk",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the all-products collection URL.
        """
        return ["https://www.greytonecoffee.co.uk/category/all-products"]

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
        try:
            soup = await super().fetch_page(*args, **kwargs)
            url = kwargs.get("url")
            if not url and len(args) > 0:
                url = args[0]
            # Only narrow product detail pages, leave listing/category pages untouched
            if "/product-page/" not in (url or ""):
                return soup
            if soup is None:
                return None
            product_el = soup.select("div[data-hook='product-page']")
            if len(product_el) == 1:
                logger.debug(f"Narrowed soup to div[data-hook='product-page'] for {url}")
                return product_el[0]
            logger.warning(f"Expected 1 div[data-hook='product-page'] for {url}, found {len(product_el)}")
            return soup
        except Exception as e:
            logger.error(f"Error fetching page {url if 'url' in dir() else '?'}: {e}")
            return None

    # Sold-out detection: Wix text detection on product-item-root container.
    # When a Wix product is sold out, the "Add to Cart" button text becomes
    # "Unavailable" / "Sold out" / "Out of stock" inside the product-item-root
    # container. We skip any product-item-root whose text contains those markers
    # before applying is_coffee_product_url filtering, so excluded products
    # don't leak past the stock check.
    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from the Wix store listing, filtering sold-out items.

        Args:
            store_url: URL of the store/category page

        Returns:
            List of in-stock product URLs
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        product_urls: list[str] = []
        seen: set[str] = set()

        for item in soup.select('[data-hook="product-item-root"]'):
            link = item.select_one('a[href*="/product-page/"]')
            if not link:
                continue
            href = link.get("href")
            if not href or not isinstance(href, str):
                continue

            # Strip query string and fragment; resolve to absolute URL
            full_url = self.resolve_url(href.split("?")[0].split("#")[0])

            # Skip sold-out products before URL-pattern filtering
            item_text = item.get_text(" ", strip=True)
            if any(marker in item_text for marker in ("Unavailable", "Sold out", "Out of stock", "SOLD OUT")):
                logger.debug(f"Skipping sold-out product: {full_url}")
                continue

            # Apply standard coffee-product URL filtering (uses /product-page/ path pattern)
            if not self.is_coffee_product_url(full_url, required_path_patterns=["/product-page/"]):
                continue

            if full_url not in seen:
                seen.add(full_url)
                product_urls.append(full_url)

        logger.info(f"Found {len(product_urls)} in-stock product URLs from {store_url}")
        return product_urls
