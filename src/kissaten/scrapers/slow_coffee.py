"""Slow Coffee Roasters scraper implementation with AI-powered extraction."""

import logging

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="slow-coffee",
    display_name="Slow Coffee Roasters",
    roaster_name="Slow Coffee Roasters",
    website="https://slowcoffee.co.nz",
    description="Specialty coffee roaster based in New Zealand.",
    requires_api_key=True,
    currency="NZD",
    country="New Zealand",
    status="available",
)
class SlowCoffeeScraper(BaseScraper):
    """Scraper for Slow Coffee Roasters (slowcoffee.co.nz) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Slow Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Slow Coffee Roasters",
            base_url="https://slowcoffee.co.nz",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the store URLs
        """
        return [
            "https://slowcoffee.co.nz/collections/espresso-coffee",
            "https://slowcoffee.co.nz/collections/filter-coffee",
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
            use_playwright=True,
            use_optimized_mode=True,
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
            product_section = soup.select("main > div.shopify-section")
            if len(product_section) > 0:
                # Strip x-data attributes from all elements in the product section to avoid AI confusion
                for el in product_section[0].select("*"):
                    if el.has_attr("x-data"):
                        del el["x-data"]
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
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        custom_selectors = [
            'a[href*="/products/"]',
        ]

        product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/products/"],
            selectors=custom_selectors,
        )

        excluded_products = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "accessory",
            "merchandise",
            "3-bags-of-coffee",
            "test-roast",
            "t-shirt",
            "sweatshirt",
            "matcha",
            "tumbler",
            "collection-box"
        ]
        filtered_urls = []
        for url in product_urls:
            if url and isinstance(url, str) and not any(excluded in url.lower() for excluded in excluded_products):
                filtered_urls.append(url)

        return filtered_urls
