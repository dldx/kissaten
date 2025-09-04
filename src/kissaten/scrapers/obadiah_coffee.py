"""Obadiah Coffee scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="obadiah",
    display_name="Obadiah Coffee",
    roaster_name="Obadiah Coffee",
    website="https://obadiahcoffee.com",
    description="UK-based specialty coffee roaster focusing on seasonal coffees and single origins",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class ObadiahCoffeeScraper(BaseScraper):
    """Scraper for Obadiah Coffee (obadiahcoffee.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Obadiah Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Obadiah Coffee",
            base_url="https://obadiahcoffee.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the store URL
        """
        return ["https://obadiahcoffee.com/pages/seasonal-coffees"]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Obadiah Coffee store using AI extraction.

        Returns:
            List of CoffeeBean objects
        """
        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=self._extract_product_urls_from_store,
            ai_extractor=self.ai_extractor,
            use_playwright=False,
        )

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

        # First, find the collection div as requested
        collection_div = soup.find("div", class_="collection")
        if collection_div and hasattr(collection_div, 'find_all'):
            # Search within the collection div only - create new BeautifulSoup from it
            from bs4 import BeautifulSoup
            search_soup = BeautifulSoup(str(collection_div), 'html.parser')
        else:
            # Fallback to entire page if collection div not found
            search_soup = soup

        # Custom selectors for Obadiah Coffee (Shopify-based)
        custom_selectors = [
            'a[href*="/products/"]',
            '.product-item a',
            '.grid__item a',
            'a.product-link',
            'h3 a',  # Product title links
        ]

        return self.extract_product_urls_from_soup(
            search_soup,
            url_path_patterns=["/products/"],
            selectors=custom_selectors,
        )
