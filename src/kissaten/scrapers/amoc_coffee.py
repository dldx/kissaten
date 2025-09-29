"""AMOC (A Matter of Concrete) Coffee scraper implementation with AI-powered extraction."""

import logging
from pathlib import Path

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="amoc",
    display_name="AMOC Coffee",
    roaster_name="A Matter of Concrete",
    website="https://amatterofconcrete.com",
    description="Netherlands-based specialty coffee roaster from Rotterdam",
    requires_api_key=True,
    currency="EUR",
    country="Netherlands",
    status="available",
)
class AmocCoffeeScraper(BaseScraper):
    """Scraper for AMOC (A Matter of Concrete) Coffee with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize AMOC Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="A Matter of Concrete",
            base_url="https://amatterofconcrete.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the coffee category URL
        """
        return ["https://amatterofconcrete.com/product-category/coffee/all/"]


    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction.

        Args:
            product_urls: List of URLs for new products

        Returns:
            List of newly scraped CoffeeBean objects
        """
        if not product_urls:
            return []

        # Create a function that returns the product URLs for the AI extraction
        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=True,  # AMOC uses Playwright for JavaScript-rendered content
        )

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from store page.

        Args:
            store_url: URL of the store page

        Returns:
            List of product URLs
        """
        soup = await self.fetch_page(store_url, use_playwright=True)
        if not soup:
            return []

        # Custom selectors for AMOC's WooCommerce store
        custom_selectors = [
            ".woocommerce-LoopProduct-link",  # Main product title links
            '.product-small a[href*="/product/"]',  # Product container links
            'a[aria-label][href*="/product/"]',  # Image links with aria-label
            '.box-image a[href*="/product/"]',  # Image container links
            'a[href*="/product/"]',  # Fallback for any product links
        ]

        # Extract all product URLs using the base class method
        all_product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/product/"],
            selectors=custom_selectors,
        )

        # Filter coffee products using base class method
        coffee_urls = []
        for url in all_product_urls:
            if self.is_coffee_product_url(url, required_path_patterns=["/product/"]):
                coffee_urls.append(url)

        logger.info(f"Found {len(coffee_urls)} coffee product URLs out of {len(all_product_urls)} total products")
        return coffee_urls
