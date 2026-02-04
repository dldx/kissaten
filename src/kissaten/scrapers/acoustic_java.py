"""Elixr Coffee Roaster scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


@register_scraper(
    name="acoustic-java",
    display_name="Acoustic Java",
    roaster_name="Acoustic Java",
    website="https://acousticjava.com",
    description="Specialty coffee roaster based in Worcester, MA",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="available",
)
class AcousticJavaScraper(BaseScraper):
    """Scraper for Acoustic Java (acousticjava.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Acoustic Java scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Acoustic Java",
            base_url="https://acousticjava.com",
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
            "https://acousticjava.com/collections/light-roast",
            "https://acousticjava.com/collections/medium-roast",
            "https://acousticjava.com/collections/dark-roast",
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
            product_section = soup.select("div.shop-details-single-product-head")
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
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        # Custom selectors for Elixr Coffee Roaster (Shopify-based)
        custom_selectors = [
            'a[href*="/products/"]',
            ".product-item a",
            ".grid__item a",
            "a.product-link",
            "h3 a",  # Product title links
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
