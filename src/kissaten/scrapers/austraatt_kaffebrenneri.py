"""Austrått Kaffebrenneri scraper implementation with AI-powered extraction."""

import logging

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="austraatt-kaffebrenneri",
    display_name="Austrått Kaffebrenneri",
    roaster_name="Austrått Kaffebrenneri",
    website="https://www.austraattkaffebrenneri.no",
    description="Norwegian specialty coffee roastery based in Voll, offering single-origin "
    "coffees and espresso blends.",
    requires_api_key=True,
    currency="NOK",
    country="Norway",
    status="available",
)
class AustraattKaffebrenneriScraper(BaseScraper):
    """Scraper for Austrått Kaffebrenneri with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Austrått Kaffebrenneri scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Austrått Kaffebrenneri",
            base_url="https://www.austraattkaffebrenneri.no",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List of coffee category URLs.
        """
        return ["https://www.austraattkaffebrenneri.no/categories/kaffe"]

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page and return a reduced soup for AI extraction.

        For product pages, trim the soup down to the main product section
        (``main > section``) which contains the title, description, options
        and price - everything the AI extractor needs. Drops the rest of the
        page (header, footer, related products, reviews widgets, etc.) to
        reduce token count.

        Args:
            *args: Positional args forwarded to ``super().fetch_page``.
            **kwargs: Keyword args forwarded to ``super().fetch_page``.

        Returns:
            Reduced BeautifulSoup/Tag, or None if the fetch failed.
        """
        try:
            soup = await super().fetch_page(*args, **kwargs)
            url = kwargs.get("url")
            if not url and len(args) > 0:
                url = args[0]

            if not isinstance(soup, (BeautifulSoup, Tag)) or "/products/" not in (url or ""):
                return soup

            section = soup.select_one("main > section")
            if not section:
                return soup

            trimmed = BeautifulSoup("", "lxml")
            trimmed.append(section)
            logger.debug(f"Trimmed product page to main section: {url}")
            return trimmed
        except Exception as e:
            logger.error(f"Error fetching page {kwargs.get('url') or (args[0] if args else '?')}: {e}")
            return None

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
            translate_to_english=True,
        )

    def _get_excluded_url_patterns(self) -> list[str]:
        """Exclude non-bean products from the Austrått catalogue.

        Returns:
            List of URL patterns to exclude.
        """
        return super()._get_excluded_url_patterns() + [
            "espresso-og-baristamaskin",  # Espresso/barista coffee blend (not a single-origin bean)
            "abonnement",  # Subscription products
            "subscription",
            "brew-bag",
            "drip-bag",
            "capsule",
            "pod",
        ]

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Force currency to NOK regardless of AI detection."""
        bean.currency = "NOK"
        return super().postprocess_extracted_bean(bean)

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from a Kaffe category page.

        Sold-out detection: text detection. Each product card contains a
        ``pb_stock_info`` block that says "På lager" (in stock) for available
        products and "Ikke på lager" / "Utsolgt" for sold-out ones. We skip
        cards that don't include the "På lager" marker before the standard
        coffee URL filter runs.

        Args:
            store_url: URL of the store page

        Returns:
            List of in-stock product URLs
        """
        soup = await self.fetch_page(store_url, use_playwright=False)
        if not soup:
            return []

        product_urls: list[str] = []
        for card in soup.select("article.product-thumb-info"):
            # Sold-out detection: text (Norwegian "På lager" = in stock)
            stock_info = card.select_one(".pb_stock_info")
            stock_text = stock_info.get_text(" ", strip=True) if stock_info else card.get_text(" ", strip=True)
            if "På lager" not in stock_text:
                logger.debug(f"Skipping sold-out product on {store_url}")
                continue

            link = card.select_one('a[href*="/products/"]')
            if not isinstance(link, Tag):
                continue
            href = link.get("href")
            if not href or not isinstance(href, str):
                continue

            full_url = self.resolve_url(href).split("?")[0]
            if self.is_coffee_product_url(full_url, required_path_patterns=["/products/"]):
                product_urls.append(full_url)

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_urls: list[str] = []
        for url in product_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        logger.info(f"Found {len(unique_urls)} in-stock product URLs from {store_url}")
        return unique_urls
