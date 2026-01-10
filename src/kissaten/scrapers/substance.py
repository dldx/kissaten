"""Substance Café scraper implementation with AI-powered extraction."""

import logging

from bs4 import BeautifulSoup

from kissaten.schemas.coffee_bean import PriceOption

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="substance-cafe",
    display_name="Substance Café",
    roaster_name="Substance Café",
    website="https://substancecafe.com",
    description="Specialty coffee roaster and café based in Paris, France.",
    requires_api_key=True,
    currency="EUR",
    country="France",
    status="available",
)
class SubstanceCafeScraper(BaseScraper):
    """Scraper for Substance Café with AI-powered extraction."""
    def __init__(self, api_key: str | None = None):
        """Initialize Coffee Collective scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Substance Café",
            base_url="https://substancecafe.com",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the coffee collection URLs
        """
        return [
            "https://www.substancecafe.com/boutique/",
        ]

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | None:
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
            if "/product" not in (url or ""):
                return soup  # Only modify product pages
            # Return product element
            product_el = soup.select("div.product")
            if len(product_el) > 0:
                return product_el[0]
            return soup
        except Exception as e:
            logger.error(f"Error fetching page {url}: {e}")
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
        )

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from store page.

        Args:
            store_url: URL of the store page

        Returns:
            List of product URLs
        """
        soup = await self.fetch_page(store_url)
        # Get first product grid
        product_grid = soup.select("ul.products")

        if not product_grid:
            return []

        # Get all product URLs using the base class method
        product_urls = self.extract_product_urls_from_soup(
            product_grid[0],
            url_path_patterns=["/product/"],
            selectors=[
                # Generic product link selectors
                'a[href*="/product/"]',
            ],
        )

        # Filter out non-coffee products (subscriptions, trios, merchandise, etc.)
        excluded_products = [
            "abaca-filters",
        ]

        filtered_urls = []
        for url in product_urls:
            # Check if any excluded product identifier is in the URL
            url_lower = url.lower()
            if not any(excluded in url_lower for excluded in excluded_products):
                filtered_urls.append(url)

        return list(set(filtered_urls))
