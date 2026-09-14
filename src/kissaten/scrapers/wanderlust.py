"""Wanderlust Espresso scraper implementation with AI-powered extraction (Wix storefront)."""

import logging

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="wanderlust-espresso",
    display_name="Wanderlust Espresso",
    roaster_name="Wanderlust Espresso",
    website="https://www.wanderlust-espresso.com",
    description="Specialty coffee roaster and mobile coffee bar in Richmond Upon Thames, "
    "United Kingdom, selling roasted coffee beans online alongside brewing kit and event services.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class WanderlustEspressoScraper(BaseScraper):
    """Scraper for Wanderlust Espresso (wanderlust-espresso.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Wanderlust Espresso scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Wanderlust Espresso",
            base_url="https://www.wanderlust-espresso.com",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the coffee beans shop page URL.
        """
        return ["https://www.wanderlust-espresso.com/coffee-beans"]

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Pin the store currency to GBP.

        The Wix product pages carry no ``og:price:currency`` meta tag (currency
        only appears inside the embedded rendered-state JSON), so the base
        currency detection never fires. Pin GBP so a misdetected default can
        never stamp the wrong currency onto beans.

        Args:
            bean: Extracted CoffeeBean object

        Returns:
            Postprocessed CoffeeBean object
        """
        bean.currency = "GBP"
        return bean

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
            # Only narrow product detail pages, leave listing pages untouched
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

    # Sold-out detection: Wix text detection on the product-item-root container
    # (case-insensitive). When a Wix product is sold out, the add-to-cart button
    # inside the product-item-root container reads "Out of Stock" / "Sold out" /
    # "Unavailable" and is disabled. We skip any product-item-root whose text
    # contains those markers before applying is_coffee_product_url filtering, so
    # excluded products don't leak past the stock check.
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

        sold_out_markers = ("unavailable", "sold out", "out of stock")

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
            item_text = item.get_text(" ", strip=True).lower()
            if any(marker in item_text for marker in sold_out_markers):
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
