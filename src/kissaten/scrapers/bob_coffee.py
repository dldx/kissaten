""" BOB Coffee Lab scraper implementation with AI-powered extraction."""

import logging

from kissaten.schemas.coffee_bean import CoffeeBean

from ..ai import CoffeeDataExtractor
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="bob-coffee",
    display_name="BOB Coffee Lab",
    roaster_name="BOB Coffee Lab",
    website="https://bob.coffee",
    description="Specialty coffee roaster based in Romania",
    requires_api_key=True,
    currency="RON",
    country="Romania",
    status="available",
)
class BOBCoffeeScraper(BaseScraper):
    """Scraper with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="BOB Coffee Lab",
            base_url="https://bob.coffee",
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
            "https://bob.coffee/en/3-coffee",
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
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=False,
            use_optimized_mode=False,
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

        # Get first two collection grids
        all_product_urls = []
        # Extract all product URLs
        all_product_url_el = soup.select('a[href*="/coffee/"]')
        for el in all_product_url_el:
            if "Sold out" not in el.parent.parent.text:
                all_product_urls.append(el['href'])

        # Filter coffee products using base class method
        excluded_patterns = []
        coffee_urls = []
        for url in all_product_urls:
            if self.is_coffee_product_url(url, required_path_patterns=["/coffee/"]) and not any(
                pattern in url for pattern in excluded_patterns
            ):
                coffee_urls.append(url)

        logger.info(f"Found {len(coffee_urls)} coffee product URLs out of {len(all_product_urls)} total products")
        return list(set(coffee_urls))
