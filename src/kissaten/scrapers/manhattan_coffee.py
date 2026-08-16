"""Manhattan Coffee Roasters scraper implementation with AI-powered extraction.

Manhattan Coffee Roasters (manhattancoffeeroasters.com) is a Rotterdam,
Netherlands roaster. The storefront is WooCommerce on WordPress: the coffee
catalogue lives under a dedicated ``/products/coffees/`` category page whose
product cards are standard ``li.product`` elements (with the WooCommerce
``outofstock`` class on sold-out cards) and product detail pages use the
WooCommerce ``div.product`` container.
"""

import logging

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="manhattan-coffee",
    display_name="Manhattan Coffee Roasters",
    roaster_name="Manhattan",
    website="https://manhattancoffeeroasters.com",
    description="Rotterdam, Netherlands specialty coffee roaster (WooCommerce).",
    requires_api_key=True,
    currency="EUR",
    country="Netherlands",
    status="available",
)
class ManhattanCoffeeScraper(BaseScraper):
    """Scraper for Manhattan Coffee Roasters (manhattancoffeeroasters.com)."""

    def __init__(self, api_key: str | None = None):
        """Initialize the Manhattan scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Manhattan",
            base_url="https://manhattancoffeeroasters.com",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page and narrow WooCommerce product detail pages to ``div.product``.

        WooCommerce product detail pages embed all useful content inside the
        ``div.product`` container (title, price, tasting notes, description).
        Narrowing the soup to that container strips the nav, footer, JS blobs,
        and unrelated markup before the HTML is sent to the AI extractor, which
        keeps token usage low. Listing/category pages are left untouched.

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
            # Only narrow product detail pages ("/product/coffees/..."),
            # leave the listing category page ("/products/coffees/") untouched.
            if "/product/" not in (url or ""):
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

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape (the dedicated Coffees category)."""
        return ["https://manhattancoffeeroasters.com/products/coffees/"]

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
        )

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        # WooCommerce pages have no og:price:currency meta tag, so the base
        # class currency detection never fires and default_currency falls back
        # to the registry default. Manhattan prices in EUR; force it.
        bean.currency = "EUR"
        return bean

    # Sold-out detection: WooCommerce class detection on the product card.
    # Manhattan (WooCommerce) marks sold-out products by adding the
    # ``outofstock`` class to the ``li.product`` card. We skip any card whose
    # class list contains ``outofstock`` (or ``sold-out``/``oos``) before
    # applying is_coffee_product_url filtering, so excluded products don't leak
    # past the stock check.
    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract in-stock product URLs from the Coffees category page.

        Args:
            store_url: URL of the store/category page

        Returns:
            List of in-stock coffee product URLs
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        product_urls: list[str] = []
        seen: set[str] = set()

        cards = soup.select("li.product") or soup.select(".product")
        for card in cards:
            classes = " ".join(card.get("class") or [])
            # Skip sold-out products (WooCommerce 'outofstock' on the card).
            if any(token in classes for token in ("outofstock", "sold-out", "oos")):
                continue
            link = card.select_one('a[href*="/product/"]')
            if not link:
                continue
            href = link.get("href")
            if not href or not isinstance(href, str):
                continue
            full_url = self.resolve_url(href)
            # Apply coffee filtering before adding so non-coffee products
            # (merchandise, subscriptions, gear) are kept out.
            if self.is_coffee_product_url(full_url, required_path_patterns=["/product/"]):
                if full_url not in seen:
                    seen.add(full_url)
                    product_urls.append(full_url)

        logger.info(f"Found {len(product_urls)} in-stock coffee product URLs from {store_url}")
        return product_urls
