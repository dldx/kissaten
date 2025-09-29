"""People's Possession Coffee scraper implementation with AI-powered extraction."""

import logging
from pathlib import Path

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="people-possession",
    display_name="People's Possession",
    roaster_name="People's Possession",
    website="https://peoplepossession.com",
    description="Radically sourced specialty coffee from Europe",
    requires_api_key=True,
    currency="EUR",
    country="Europe",
    status="available",
)
class PeoplePossessionScraper(BaseScraper):
    """Scraper for People's Possession Coffee (peoplepossession.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize People's Possession scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="People's Possession",
            base_url="https://peoplepossession.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the shop URL
        """
        return ["https://peoplepossession.com/shop/"]


    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction.

        Args:
            product_urls: List of URLs for new products

        Returns:
            List of newly scraped CoffeeBean objects
        """

        # Create a function that returns the product URLs for the AI extraction
        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=True,
        )

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean:
        """People's possession product pages are missing if product is sold out.
        AI extraction fails to detect if product is in stock.
        Override to always set in_stock to True"""
        bean.in_stock = True
        return bean

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

        # Custom selectors for People's Possession
        custom_selectors = [
            'a[href*="/product/"]',
            ".product-item a",
            ".collection-item a",
            'a[class*="product"]',
        ]

        # Extract all product URLs using the base class method
        all_product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/product/"],
            selectors=custom_selectors,
        )

        # Filter coffee products
        coffee_urls = []
        excluded_patterns = ["/lid", "/posters", "/coin"]
        for url in all_product_urls:
            if self.is_coffee_product_url(url, required_path_patterns=["/product/"]) and not any(
                excluded in url.lower() for excluded in excluded_patterns
            ):
                coffee_urls.append(url)

        logger.info(f"Found {len(coffee_urls)} coffee product URLs out of {len(all_product_urls)} total products")
        return coffee_urls
