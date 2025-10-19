"""Curve Coffee Roasters scraper.

UK-based specialty coffee roaster offering single origin coffees with detailed
origin stories and producer information.
"""

import logging
from pathlib import Path

from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="curve-coffee",
    display_name="Curve Coffee Roasters",
    roaster_name="Curve Coffee Roasters",
    website="https://www.curveroasters.co.uk",
    description="UK specialty coffee roaster offering single origin coffees "
    "with detailed origin stories and producer information",
    requires_api_key=True,  # Using AI extraction for complex Squarespace site
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class CurveCoffeeScraper(BaseScraper):
    """Scraper for Curve Coffee Roasters."""

    def __init__(self, api_key: str | None = None):
        """Initialize the scraper.

        Args:
            api_key: Optional API key for AI-powered extraction
        """
        super().__init__(
            roaster_name="Curve Coffee Roasters",
            base_url="https://www.curveroasters.co.uk",
            rate_limit_delay=1.5,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor (recommended for complex Squarespace sites)
        self.ai_extractor = None
        try:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
        except ImportError:
            logger.warning("AI extractor not available - falling back to traditional extraction")

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the store URLs to scrape
        """
        return [
            "https://www.curveroasters.co.uk/shop-coffee?category=Coffee",
            # Could also include other coffee categories if needed:
            # "https://www.curveroasters.co.uk/shop-coffee?category=Espresso",
            # "https://www.curveroasters.co.uk/shop-coffee?category=Filter",
            # "https://www.curveroasters.co.uk/shop-coffee?category=Decaf",
        ]

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

        # Use the base class method with Squarespace-specific patterns
        urls = self.extract_product_urls_from_soup(
            soup,
            # Curve Coffee product URL pattern
            url_path_patterns=["/shop-coffee/"],
            selectors=[
                # Squarespace product link selectors
                'a[href*="/shop-coffee/"]',
                ".sqs-block-image a",
                ".summary-title a",
                ".summary-item a",
                "a.summary-excerpt-only",
                # Coffee-specific exclusions will be handled by the filtering
            ],
        )

        return self.deduplicate_urls(urls)

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
            use_playwright=True,
        )