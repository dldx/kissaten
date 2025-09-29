"""Caravan Coffee scraper implementation with AI-powered extraction."""

import logging
from pathlib import Path

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="caravan-coffee",
    display_name="Caravan Coffee",
    roaster_name="Caravan Coffee",
    website="https://caravanandco.com",
    description="London-based specialty coffee roaster",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class CaravanCoffeeScraper(BaseScraper):
    """Scraper for Caravan Coffee with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Caravan Coffee",
            base_url="https://caravanandco.com",
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
        return [
            "https://caravanandco.com/collections/new-coffee?filter.p.m.filter.brew_style=Espresso&filter.p.m.filter.brew_style=Filter&sort_by=manual",
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

        # Create a function that returns the product URLs for the AI extraction
        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls, ai_extractor=self.ai_extractor, use_playwright=False
        )

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from store page.

        Args:
            store_url: URL of the store page

        Returns:
            List of product URLs
        """
        soup = await self.fetch_page(store_url, use_playwright=False)
        if not soup:
            return []

        # Extract all product URLs using the base class method
        all_product_url_el = soup.select('.product-grid a[href*="/products/"][aria-labelledby*="CardLink-template"]')
        all_product_urls = []
        for el in all_product_url_el:
            if not "Sold out" in el.parent.parent.parent.text:
                all_product_urls.append(f"{self.base_url}{el['href'].split('?')[0]}")

        excluded_patterns = ["roasters-rotation"]
        # Filter coffee products using base class method
        coffee_urls = []
        for url in all_product_urls:
            if self.is_coffee_product_url(url, required_path_patterns=["/products/"]) and not any(
                pattern in url for pattern in excluded_patterns
            ):
                coffee_urls.append(url)

        logger.info(f"Found {len(coffee_urls)} coffee product URLs out of {len(all_product_urls)} total products")
        return coffee_urls
