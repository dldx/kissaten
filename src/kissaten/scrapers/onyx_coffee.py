"""Onyx Coffee Lab EU scraper implementation with AI-powered extraction.

Handles the EU site:
- EU: https://onyxcoffeelab.eu/collections/eu-coffee
"""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="onyx-coffee",
    display_name="Onyx Coffee Lab EU",
    roaster_name="Onyx Coffee Lab",
    website="https://onyxcoffeelab.eu",
    description="Specialty coffee roaster EU operations",
    requires_api_key=True,
    currency="EUR",
    country="Netherlands",
    status="available",
)
class OnyxCoffeeScraper(BaseScraper):
    """Scraper for Onyx Coffee Lab EU site with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Onyx Coffee EU scraper.

        Args:
            api_key: API key for AI extraction. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Onyx Coffee Lab",
            base_url="https://onyxcoffeelab.eu",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape from Onyx Coffee Lab EU.

        Returns:
            List containing the EU store URL
        """
        return [
            "https://onyxcoffeelab.eu/collections/eu-coffee",  # EU coffee collection
        ]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Onyx Coffee Lab EU site using AI extraction.

        Returns:
            List of CoffeeBean objects from the EU site
        """
        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=self._extract_product_urls_from_store,
            ai_extractor=self.ai_extractor,
            use_playwright=False,  # Shopify sites work well with simple HTTP requests
            batch_size=3,  # Conservative batch size to respect rate limits
        )

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from store page.

        Args:
            store_url: URL of the store page

        Returns:
            List of product URLs
        """
        # Use regular fetch_page to get the EU site content
        soup = await self.fetch_page(store_url)
        if not soup:
            logger.error(f"Failed to fetch store page: {store_url}")
            return []

        # Shopify-specific selectors for Onyx Coffee Lab
        custom_selectors = [
            'a[href*="/products/"]',  # General Shopify product links
            ".product-item a",  # Product item containers
            ".product-card a",  # Product card containers
            "a.product-link",  # Direct product links
            ".grid-product__link",  # Shopify grid product links
        ]

        # Extract URLs using base class method
        product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/products/"],
            selectors=custom_selectors,
        )

        logger.info(f"Extracted {len(product_urls)} product URLs from {store_url}")
        return product_urls
