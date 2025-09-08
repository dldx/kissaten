"""Atkinson's Coffee Roasters (The Coffee Hopper) scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="atkinsons-coffee",
    display_name="Atkinson's Coffee Roasters",
    roaster_name="Atkinson's Coffee Roasters",
    website="https://www.thecoffeehopper.com",
    description="Lancaster-based specialty coffee roaster offering single origins, "
    "blends, and espresso coffees",
    requires_api_key=True,
    currency="GBP",
    country="UK",
    status="available",
)
class AtkinsonsCoffeeScraper(BaseScraper):
    """Scraper for Atkinson's Coffee Roasters (thecoffeehopper.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Atkinson's Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Atkinson's Coffee Roasters",
            base_url="https://www.thecoffeehopper.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the coffee shop URL
        """
        return ["https://www.thecoffeehopper.com/shop/#category-coffees"]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Atkinson's Coffee Roasters using AI extraction.

        Returns:
            List of CoffeeBean objects
        """
        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=self._extract_product_urls_from_store,
            ai_extractor=self.ai_extractor,
            use_playwright=False,
        )

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from store page, focusing on first div.product-table only.

        Args:
            store_url: URL of the store page

        Returns:
            List of product URLs from the first product table (coffee section)
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        # Extract product URLs only from the first product table
        product_urls = [a.get("data-href") for a in soup.select(".product-table-content")[0].select('a[data-href*="/products/"]')]

        # Filter out subscription products if they exist
        filtered_urls = []
        excluded_terms = ["subscription", "gift-voucher", "gift-card", "gift-set", "espresso-duo"]

        for url in product_urls:
            if not any(term in url.lower() for term in excluded_terms):
                filtered_urls.append(url)

        return filtered_urls
