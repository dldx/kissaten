"""Coffee Wallas scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="coffee-wallas",
    display_name="Coffee Wallas",
    roaster_name="Coffee Wallas",
    website="https://coffeewallas.com",
    description="Canadian specialty coffee roaster focusing on Asian coffee origins",
    requires_api_key=True,
    currency="CAD",
    country="Canada",
    status="available",
)
class CoffeeWallasScraper(BaseScraper):
    """Scraper for Coffee Wallas (coffeewallas.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Coffee Wallas scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Coffee Wallas",
            base_url="https://coffeewallas.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the coffee collection URL
        """
        return ["https://coffeewallas.com/collections/frontpage"]


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

        excluded_patterns = ["will-it-blend-"]
        # Use the new base class method with URL patterns for Shopify stores
        product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/products/"],
            selectors=[
                # Common Shopify product link selectors
                'a[href*="/products/"]',
                ".product-item a",
                ".product-link",
                ".grid-product__link",
                ".card-wrapper a",
                # Coffee Wallas specific selectors based on HTML structure
                ".product a",
                ".product-card a",
                "h3 a",  # Product title links
            ],
        )

        filtered_urls = []
        for url in product_urls:
            if not any(excluded in url.lower() for excluded in excluded_patterns):
                filtered_urls.append(url)
        return filtered_urls
