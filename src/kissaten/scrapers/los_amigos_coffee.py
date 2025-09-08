"""Los Amigos Coffee scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="los-amigos-coffee",
    display_name="Los Amigos Coffee",
    roaster_name="Los Amigos Coffee",
    website="https://www.losamigoscoffee.com",
    description="Specialty coffee roaster offering unique blends and single origins",
    requires_api_key=True,
    currency="USD",
    country="USA",
    status="available",
)
class LosAmigosCoffeeScraper(BaseScraper):
    """Scraper for Los Amigos Coffee (losamigoscoffee.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Los Amigos Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Los Amigos Coffee",
            base_url="https://www.losamigoscoffee.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the coffee collection URLs
        """
        return [
            "https://www.losamigoscoffee.com/category/blends",
            "https://www.losamigoscoffee.com/category/tanzania-the-big-3-1",  # Tanzania specialty collection
        ]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Los Amigos Coffee using AI extraction.

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

        # Get all product URLs using the base class method
        product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/product-page/"],
            selectors=[
                # Wix-based store selectors
                'a[href*="/product-page/"]',
                '.product-item a',
                '.product-link',
                # Los Amigos specific selectors based on HTML structure
                '.product a',
                'a[data-testid*="product"]',
            ],
        )

        # Filter out excluded products (merchandise and non-coffee items)
        excluded_products = [
            "tee",  # T-shirts and merchandise
            "sticker",  # Stickers and merchandise
            "merch",  # General merchandise
        ]

        filtered_urls = []
        for url in product_urls:
            # Check if any excluded product identifier is in the URL
            if not any(excluded in url.lower() for excluded in excluded_products):
                filtered_urls.append(url)

        return filtered_urls
