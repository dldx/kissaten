"""Style Coffee scraper implementation with AI-powered extraction (BASE platform, Japan)."""

import logging

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)

# Sold-out marker substrings for BASE (thebase.in) item cards. BASE stores
# sold-out status in card/history text using Japanese ("売り切れ" = sold out,
# "品切れ" = out of stock) and the English "SOLD OUT"/"sold out" variants.
_SOLD_OUT_MARKERS = ("売り切れ", "品切れ", "完売", "SOLD OUT", "Sold out", "sold out")


@register_scraper(
    name="style",
    display_name="Style Coffee",
    roaster_name="Style",
    website="https://www.stylecoffee.jp/",
    description="Japanese specialty coffee roaster based in Tokyo, known for their "
    "Ethiopia Anasora, Honduras, and Kenya single origins",
    requires_api_key=True,
    currency="JPY",  # Japanese Yen
    country="Japan",
    status="available",
)
class StyleScraper(BaseScraper):
    """Scraper for Style Coffee (stylecoffee.jp) with AI-powered extraction.

    Style Coffee is hosted on the Japanese BASE e-commerce platform
    (thebase.in). Product detail pages live under ``/items/<id>`` and the
    coffee catalogue is the "BEANS" category.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Style Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Style",
            base_url="https://www.stylecoffee.jp",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the coffee "BEANS" category URL.
        """
        return ["https://www.stylecoffee.jp/categories/1487592"]

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

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page and narrow product detail pages to the BASE item container.

        BASE product detail pages embed all useful content inside
        ``div.item-detail-inner``. Narrowing the soup to that container strips
        nav, footer, JSON blobs, and unrelated markup before the HTML is sent
        to the AI extractor, which dramatically reduces token noise.

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
            if "/items/" not in (url or ""):
                return soup
            if soup is None:
                return None
            container = soup.select("div.item-detail-inner")
            if len(container) == 1:
                logger.debug(f"Narrowed soup to div.item-detail-inner for {url}")
                return container[0]
            logger.warning(f"Expected 1 div.item-detail-inner for {url}, found {len(container)}")
            return soup
        except Exception as e:
            logger.error(f"Error fetching page {url if 'url' in dir() else '?'}: {e}")
            return None

    # Sold-out detection: BASE text detection on the item-card container
    # (div.item.part). BASE marks a sold-out product by injecting a sold-out /
    # "売り切れ" label into the card; we skip any card whose text contains a
    # sold-out marker before applying is_coffee_product_url, so excluded
    # products don't leak past the stock check.
    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from the BASE BEANS category, filtering sold-out items.

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

        for card in soup.select("div.item.part"):
            link = card.select_one('a[href*="/items/"]')
            if not link:
                continue
            href = link.get("href")
            if not href or not isinstance(href, str):
                continue

            # Strip query string and fragment; resolve to absolute URL
            full_url = self.resolve_url(href.split("?")[0].split("#")[0])

            # Skip sold-out products before URL-pattern filtering
            card_text = card.get_text(" ", strip=True)
            if any(marker in card_text for marker in _SOLD_OUT_MARKERS):
                logger.debug(f"Skipping sold-out product: {full_url}")
                continue

            # Apply standard coffee-product URL filtering (uses /items/ path pattern)
            if not self.is_coffee_product_url(full_url, required_path_patterns=["/items/"]):
                continue

            if full_url not in seen:
                seen.add(full_url)
                product_urls.append(full_url)

        logger.info(f"Found {len(product_urls)} in-stock product URLs from {store_url}")
        return product_urls
