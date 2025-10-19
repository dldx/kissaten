"""Cartwheel Coffee scraper implementation with AI-powered extraction."""

import logging
from pathlib import Path

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="cartwheel",
    display_name="Cartwheel Coffee",
    roaster_name="Cartwheel Coffee",
    website="https://cartwheelcoffee.com",
    description="UK-based specialty coffee roaster",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class CartwheelCoffeeScraper(BaseScraper):
    """Scraper for Cartwheel Coffee (cartwheelcoffee.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Cartwheel Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Cartwheel Coffee",
            base_url="https://cartwheelcoffee.com",
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
        return ["https://cartwheelcoffee.com/pages/store"]


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
            use_playwright=False,
        )

    def _get_excluded_url_patterns(self) -> list[str]:
        return [pattern for pattern in super()._get_excluded_url_patterns() if "cart" not in pattern]

    def _get_excluded_url_path_patterns(self) -> list[str]:
        """Get list of URL path patterns to exclude.

        Returns:
            List of URL path patterns that indicate non-product pages
        """
        return [
            "/checkout",
            "/account",
            "/login",
            "/contact",
            "/about",
            "/shipping",
            "/privacy",
            "/terms",
            "/admin",
            "/api",
        ]

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
        # The store page has tabs, we want the "Coffee" tab
        soup = soup.select("div[data-w-tab='coffee']")[0]

        # Custom selectors for Cartwheel Coffee
        custom_selectors = [
            "a.shop-img_hover.is--store.w-inline-block",
            'a[class*="shop-img_hover"]',
            'a[href*="/products/"]',
        ]

        product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/products/"],
            selectors=custom_selectors,
        )

        logger.info(f"Found {len(product_urls)} product URLs on store page: {store_url}")
        return product_urls
