"""Scraper for Coffee Lab (coffeelab.pl) - Polish specialty coffee roaster."""

import logging

from bs4 import BeautifulSoup

from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="coffeelab",
    display_name="Coffee Lab",
    roaster_name="Coffee Lab",
    website="https://coffeelab.pl",
    description="Specialty coffee roaster from Warsaw, Poland focusing on quality and precision",
    requires_api_key=True,  # Use AI extraction for best results
    currency="PLN",
    country="Poland",
    status="available",
)
class CoffeeLabScraper(BaseScraper):
    """Scraper for Coffee Lab - Polish specialty coffee roaster."""

    def __init__(self, api_key: str | None = None):
        """Initialize the scraper.

        Args:
            api_key: Optional API key for AI-powered extraction
        """
        super().__init__(
            roaster_name="Coffee Lab",
            base_url="https://coffeelab.pl",
            rate_limit_delay=1.5,  # Be respectful to the site
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor (recommended for this site)
        self.ai_extractor = None
        try:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
        except ImportError:
            logger.warning("AI extractor not available - falling back to traditional extraction")

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Coffee Lab has paginated coffee listings and multiple categories.

        Returns:
            List containing the store URLs to scrape
        """
        return [
            # Main coffee page (page 1)
            "https://coffeelab.pl/en/3-coffee",
            # Page 2 of coffee
            "https://coffeelab.pl/en/3-coffee?page=2",
            # We could also scrape specific categories, but the main coffee page
            # seems to include all products across categories
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
            use_playwright=False,
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

        # Use the base class method with Coffee Lab specific patterns
        return self.extract_product_urls_from_soup(
            soup,
            # Coffee Lab URL patterns - products are in different categories
            url_path_patterns=[
                "/en/filter/",
                "/en/espresso/",
                "/en/magic-beans/",
                "/en/brewlab/",
                "/en/cascara/",
                "/en/omniroast/",
            ],
            selectors=[
                # Try specific selectors for Coffee Lab
                'a[href*="/en/filter/"]',
                'a[href*="/en/espresso/"]',
                'a[href*="/en/magic-beans/"]',
                'a[href*="/en/brewlab/"]',
                'a[href*="/en/cascara/"]',
                'a[href*="/en/omniroast/"]',
                # Fallback selectors
                ".product-item a",
                "a.product-link",
            ],
        )
