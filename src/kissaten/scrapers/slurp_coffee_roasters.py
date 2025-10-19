"""Plot Roasting scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="slurp-coffee-roasters",
    display_name="Slurp Coffee Roasters",
    roaster_name="Slurp Coffee Roasters",
    website="https://slurpcoffeeroasters.com.ua/",
    description="Ukrainian specialty coffee roaster focused on high-quality beans",
    requires_api_key=True,
    currency="UAH",
    country="Ukraine",
    status="available",
)
class SlurpCoffeeRoastersScraper(BaseScraper):
    """Scraper with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Slurp Coffee Roasters",
            base_url="https://slurpcoffeeroasters.com.ua/",
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
        return ["https://slurpcoffeeroasters.com.ua/kava/", "https://slurpcoffeeroasters.com.ua/kava/filter/page=2/"]


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
            translate_to_english=True,
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

        # Use the base class method with standard Shopify patterns
        product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/"],
            selectors=[
                'a.catalogCard-image:not(.__grayscale)',
            ],
        )

        excluded_products = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "accessory",
            "merchandise",
            "test-roast",
        ]
        filtered_urls = []
        for url in product_urls:
            if url and isinstance(url, str) and not any(excluded in url.lower() for excluded in excluded_products):
                filtered_urls.append(url)

        return filtered_urls
