"""Moklair scraper implementation with AI-powered extraction (WooCommerce)."""

import logging

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="moklair",
    display_name="Moklair",
    roaster_name="Moklair",
    website="https://www.moklair.com",
    description="French specialty coffee roaster based in Reims, France (WooCommerce, "
    "English storefront at moklair.fr/en).",
    requires_api_key=True,
    currency="EUR",  # Euro
    country="France",
    status="available",
)
class MoklairScraper(BaseScraper):
    """Scraper for Moklair (moklair.com / moklair.fr) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Moklair scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Moklair",
            base_url="https://moklair.fr",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape (English boutique listing, paginated)."""
        return [
            "https://moklair.fr/en/boutique/",
            "https://moklair.fr/en/boutique/page/2/",
        ]

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
            translate_to_english=False,  # English storefront (/en/ URLs)
        )

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Force the currency to EUR.

        Moklair is a French roaster selling in euros (the site has no
        og:price:currency meta tag, so the AI extractor's default-GBP fallback
        mislabels the price). The EUR price is authoritative.

        Args:
            bean: Extracted CoffeeBean object

        Returns:
            The bean with currency forced to EUR
        """
        bean.currency = "EUR"
        return bean

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page and narrow product detail pages to the WooCommerce product container.

        WooCommerce single-product pages embed all useful content (summary, short
        description, tabs) inside ``div#product-<id>``. Narrowing the soup to that
        container strips nav, footer, JSON blobs, and unrelated markup before the
        HTML is sent to the AI extractor, which dramatically reduces token noise.

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
            # Only narrow product detail pages, leave listing pages untouched.
            # Listing URLs are /en/boutique/..., product URLs are /en/product/...
            if "/product/" not in (url or ""):
                return soup
            if soup is None:
                return None
            # WooCommerce single-product wrapper carries id="product-<post_id>".
            # This is unambiguous (the listing cards are li.product, not div#product-*).
            product_el = soup.select('div[id^="product-"]')
            if len(product_el) == 1:
                logger.debug(f"Narrowed soup to div#product-* for {url}")
                return product_el[0]
            logger.warning(f"Expected 1 div#product-* for {url}, found {len(product_el)}")
            return soup
        except Exception as e:
            logger.error(f"Error fetching page: {e}")
            return None

    # Sold-out detection: WooCommerce `outofstock` class on the product card.
    # Each listing card is a `li.product` whose class list includes `outofstock`
    # when the item cannot be purchased. We skip those cards before applying
    # is_coffee_product_url filtering, so excluded products don't leak past the
    # stock check.
    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from the WooCommerce listing, filtering sold-out items.

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

        for card in soup.select("li.product"):
            classes = card.get("class") or []
            if "outofstock" in classes:
                logger.debug(f"Skipping sold-out product card: {store_url}")
                continue

            link = card.select_one('a[href*="/product/"]')
            if not link:
                continue
            href = link.get("href")
            if not href or not isinstance(href, str):
                continue

            # Strip query string and fragment; resolve to absolute URL
            full_url = self.resolve_url(href.split("?")[0].split("#")[0])

            # Apply standard coffee-product URL filtering (uses /product/ path pattern)
            if not self.is_coffee_product_url(full_url):
                logger.debug(f"Excluding non-coffee product URL: {full_url}")
                continue

            if full_url not in seen:
                seen.add(full_url)
                product_urls.append(full_url)

        logger.info(f"Found {len(product_urls)} in-stock product URLs from {store_url}")
        return product_urls
