"""Back Baza Coffeescraper implementation with AI-powered extraction."""

import logging

from bs4 import BeautifulSoup

from kissaten.schemas.coffee_bean import PriceOption

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="blackbaza-coffee",
    display_name="Black Baza Coffee",
    roaster_name="Black Baza Coffee",
    website="https://www.blackbazacoffee.com",
    description="Specialty coffee roaster with a focus on sustainable practices based in India.",
    requires_api_key=True,
    currency="INR",
    country="India",
    status="available",
)
class BlackBazaCoffeeScraper(BaseScraper):
    """Scraper for Black Baza Coffee with AI-powered extraction."""
    def __init__(self, api_key: str | None = None):
        """Initialize Coffee Collective scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Black Baza Coffee",
            base_url="https://www.blackbazacoffee.com",
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
            "https://www.blackbazacoffee.com/collections/coffee",
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
        product_grid = soup.select("ul.product-grid")

        if not product_grid:
            return []

        # Get all product URLs using the base class method
        product_els = product_grid[0].select('a.full-unstyled-link[href*="/products/"]')
        product_urls = [
            self.resolve_url(el["href"]) for el in product_els if "Sold out" not in el.parent.parent.parent.text
        ]

        # Filter out non-coffee products (subscriptions, trios, merchandise, etc.)
        excluded_products = [
            "sampler-pack",
            "bundle"
        ]

        filtered_urls = []
        for url in product_urls:
            # Check if any excluded product identifier is in the URL
            url_lower = url.lower()
            if not any(excluded in url_lower for excluded in excluded_products):
                filtered_urls.append(url)

        return list(set(filtered_urls))
