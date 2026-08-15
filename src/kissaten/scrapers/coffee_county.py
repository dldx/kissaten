"""Coffee County scraper implementation with AI-powered extraction.

Coffee County (株式会社COFFEE COUNTY) is a Japanese roaster with cafes in Tokyo,
Stock, Fukuoka and Kurume. Their online shop (shop.coffeecounty.cc) runs on the
GMO "shop-pro" platform (EUC-JP encoded, ?mode=cate / ?pid= product URLs).
"""

import logging
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)

# "COFFEE BEANS" top-level category (cbid=1276755, csid=0). This page lists
# every coffee bean (BLEND + SINGLE ORIGIN) across multiple pages (?page=N).
COFFEE_BEANS_CATEGORY_URL = "https://shop.coffeecounty.cc/?mode=cate&cbid=1276755&csid=0"


@register_scraper(
    name="coffee-county",
    display_name="Coffee County",
    roaster_name="Coffee County",
    website="https://coffeecounty.cc",
    description="Japanese specialty coffee roaster with cafés in Tokyo, Stock, Fukuoka "
    "and Kurume; single-origin and blend beans from a GMO shop-pro storefront",
    requires_api_key=True,
    currency="JPY",  # Japanese Yen
    country="Japan",
    status="available",
)
class CoffeeCountyScraper(BaseScraper):
    """Scraper for Coffee County (shop.coffeecounty.cc) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Coffee County scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try the environment variable.
        """
        super().__init__(
            roaster_name="Coffee County",
            base_url="https://shop.coffeecounty.cc",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the coffee beans category URL (paginated internally).
        """
        return [COFFEE_BEANS_CATEGORY_URL]

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
            # Site is Japanese (EUC-JP); translate for higher-quality extraction
            translate_to_english=True,
        )

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from the coffee beans category, walking pagination.

        Each product card is ``<li.productlist-unit><div class="w-k-in">
        <a href="?pid=<id>">…</a>`` with sold-out items flagged by a
        ``<p class="soldout">SOLD OUT</p>`` inside the same card.

        Args:
            store_url: URL of the store/category page

        Returns:
            List of in-stock product URLs
        """
        all_urls: list[str] = []
        seen_pages: set[str] = set()
        queue = [store_url]

        while queue:
            page_url = queue.pop(0)
            if page_url in seen_pages:
                continue
            seen_pages.add(page_url)

            soup = await self.fetch_page(page_url)
            if not soup:
                # Listing fetch failed; base.py records this so out-of-stock
                # updates are suppressed for this session.
                continue

            for link in soup.select('a[href*="pid="]'):
                href = link.get("href")
                if not href or not isinstance(href, str):
                    continue

                # Sold-out detection: text on the specific product card (the
                # <a> wrapper), never a whole-page scan. Applied before any
                # URL filtering so excluded products can't leak past stock.
                if "SOLD OUT" in link.get_text(" ", strip=True).upper():
                    logger.debug(f"Skipping sold-out product: {href}")
                    continue

                all_urls.append(self.resolve_url(href))

            next_url = self._find_next_page_url(soup, page_url)
            if next_url:
                queue.append(next_url)

        return self.deduplicate_urls(all_urls)

    @staticmethod
    def _get_page_number(url: str) -> int:
        """Return the ``page`` query value for a category URL (default 1)."""
        qs = parse_qs(urlparse(url).query)
        try:
            return int(qs.get("page", ["1"])[0])
        except (ValueError, TypeError):
            return 1

    def _find_next_page_url(self, soup: BeautifulSoup, page_url: str) -> str | None:
        """Locate the next category page link, if any."""
        current = self._get_page_number(page_url)
        target = current + 1
        for link in soup.select('a[href*="page="]'):
            href = link.get("href")
            if not href or not isinstance(href, str):
                continue
            if "mode=cate" not in href:
                continue
            full = self.resolve_url(href)
            if self._get_page_number(full) == target:
                return full
        return None
