"""96B Coffee scraper implementation with AI-powered extraction."""

import logging

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="96b-coffee",
    display_name="96B Coffee",
    roaster_name="96B Coffee",
    website="https://www.96b.co",
    description="Specialty coffee roaster, cafe, green bean producer and exporter based in Saigon, Vietnam",
    requires_api_key=True,
    currency="VND",  # Vietnamese Dong
    country="Vietnam",
    status="available",
)
class Coffee96BScraper(BaseScraper):
    """Scraper for 96B Coffee (www.96b.co) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize 96B Coffee scraper.
        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="96B Coffee",
            base_url="https://www.96b.co",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the store URL
        """
        return ["https://www.96b.co/coffee"]

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction.

        Args:
            product_urls: List of URLs for new products

        Returns:
            List of newly scraped CoffeeBean objects
        """

        # Create a function that returns the product URLs for the AI extraction
        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=False,
            use_optimized_mode=False,
        )

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page and return its BeautifulSoup object.

        Args:
            url: URL of the page to fetch
            use_playwright: Whether to use Playwright for fetching

        Returns:
            BeautifulSoup object of the page, or None if fetch failed
        """
        try:
            soup = await super().fetch_page(*args, **kwargs)
            url = kwargs.get("url")
            if not url and len(args) > 0:
                url = args[0]
            if "/products" not in (url or ""):
                return soup  # Only modify product pages
            # Find product section
            product_section = soup.select("div[data-hook='product-page']")
            if len(product_section) > 0:
                return product_section[0]
            return soup
        except Exception as e:
            logger.error(f"Error fetching page {url}: {e}")
            return None

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from store page.

        Args:
            store_url: URL of the store page

        Returns:
            List of product URLs
        """
        soup = await self.fetch_page(store_url, use_playwright=False)
        if not soup:
            return []

        # Extract all product URLs and filter out sold out items
        all_product_urls = []
        all_product_url_el = soup.select('a[data-hook="product-item-container"][href*="/product-page/"]')
        for el in all_product_url_el:
            href = el.get('href')
            if href:
                all_product_urls.append(self.resolve_url(href.replace('\n', '').strip().split('?')[0]))

        # Filter out excluded products (merchandise and non-coffee items)
        excluded_products = [
            "drip-bag",
            "cold-comfort",
            "vietnam-coffee-atlas"
        ]

        filtered_urls = []
        for url in all_product_urls:
            if url and isinstance(url, str) and not any(excluded in url.lower() for excluded in excluded_products):
                filtered_urls.append(url)

        logger.info(f"Found {len(filtered_urls)} available coffee product URLs")
        return list(set(filtered_urls))
