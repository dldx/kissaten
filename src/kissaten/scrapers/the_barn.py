"""THE BARN scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="the-barn",
    display_name="The Barn",
    roaster_name="The Barn",
    website="https://www.thebarn.de",
    description="Specialty coffee roaster based in Berlin, Germany.",
    requires_api_key=True,
    currency="EUR",
    country="Germany",
    status="available",
)
class TheBarnCoffeeScraper(BaseScraper):
    """Scraper for The Barn (thebarn.de) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize The Barn scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="The Barn",
            base_url="https://www.thebarn.de",
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
        return ["https://www.thebarn.de/collections/coffee?filter.v.availability=1",
                ]


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

        # Extract all product URLs
        all_product_urls_el = soup.select('a[href*="/products/"][id*="CardLink-template"]')

        # Filter out non-coffee products (merch, equipment, etc.)
        coffee_urls = []
        for el in all_product_urls_el:
            # Skip obvious non-coffee items based on URL patterns
            if any(pattern in el["href"].lower() for pattern in ["hario-filter"]):
                logger.debug(f"Skipping non-coffee product: {el['href']}")
                continue

            coffee_urls.append(f"{self.base_url}{el['href'].split('?')[0]}")
        coffee_urls = list(set(coffee_urls))  # Deduplicate

        logger.info(f"Found {len(coffee_urls)} coffee product URLs out of {len(all_product_urls_el)} total products")
        return coffee_urls
