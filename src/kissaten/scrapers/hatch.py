"""Hatch Coffee scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="hatch",
    display_name="Hatch",
    roaster_name="Hatch",
    website="https://hatchcrafted.com",
    description="Hatch is a specialty coffee roaster based in Markham, Ontario.",
    requires_api_key=True,
    currency="CAD",
    country="Canada",
    status="available",
)
class HatchCoffeeScraper(BaseScraper):
    """Scraper for Hatch Coffee (hatchcrafted.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Hatch Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Hatch",  # Must match registry roaster_name
            base_url="https://hatchcrafted.com",
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
        return [
            "https://hatchcrafted.com/shop",
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
        all_product_sections_el = soup.select("section")

        # Filter out non-coffee products (merch, equipment, etc.)
        excluded_slugs = ["hiflux", "alcohol", "oatside", "gamma", "experience"]
        coffee_urls = []
        for section_el in all_product_sections_el[:2]:
            product_link_els = section_el.select('a[href*="/shop/"]')
            for link_el in product_link_els:
                if any(excluded in link_el["href"] for excluded in excluded_slugs):
                    continue
                coffee_urls.append(f"{self.base_url}{link_el['href']}")
        coffee_urls = list(set(coffee_urls))  # Deduplicate

        logger.info(
            f"Found {len(coffee_urls)} coffee product URLs out of {len(all_product_sections_el)} total products"
        )
        return coffee_urls
