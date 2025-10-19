"""Five Elephant scraper implementation with AI-powered extraction."""

import logging
from pathlib import Path

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="five-elephant",
    display_name="Five Elephant",
    roaster_name="Five Elephant",
    website="https://www.fiveelephant.com",
    description="Specialty coffee roaster based in Berlin, Germany",
    requires_api_key=True,
    currency="EUR",
    country="Germany",
    status="available",
)
class FiveElephantScraper(BaseScraper):
    """Scraper for Five Elephant with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Five Elephant scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Five Elephant",
            base_url="https://www.fiveelephant.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the coffee category URL
        """
        return ["https://www.fiveelephant.com/collections/espresso", "https://www.fiveelephant.com/collections/filter-coffee-beans", "https://www.fiveelephant.com/collections/special-lots"]

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
            use_optimized_mode=False
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
        product_grids = soup.select('.collection__products')
        if not product_grids:
            logger.warning(f"No product grid found on store page: {store_url}")
            return []
        all_product_url_el = product_grids[0].select('a[href*="/products/"]')
        all_product_urls = []
        for el in all_product_url_el:
            if "Sold out" not in el.parent.text:
                all_product_urls.append(f"{self.base_url}{el['href']}")

        # Filter coffee products using base class method
        excluded_patterns = []
        coffee_urls = []
        for url in all_product_urls:
            if self.is_coffee_product_url(url, required_path_patterns=["/products/"]) and not any(
                pattern in url for pattern in excluded_patterns
            ):
                coffee_urls.append(url)

        coffee_urls = list(set(coffee_urls))

        logger.info(f"Found {len(coffee_urls)} coffee product URLs out of {len(all_product_urls)} total products")
        return coffee_urls
