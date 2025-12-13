"""Original Green Roasters scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="original-green-roasters",
    display_name="Original Green Roasters",
    roaster_name="Original Green Roasters",
    website="https://www.ogrcafe.cl",
    description="Specialty coffee roaster based in Santiago, Chile",
    requires_api_key=True,
    currency="CLP",
    country="Chile",
    status="available",
)
class OriginalGreenRoastersScraper(BaseScraper):
    """Scraper for Original Green Roasters with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Original Green Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Original Green Roasters",
            base_url="https://www.ogrcafe.cl",
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
        return [
            "https://www.ogrcafe.cl/cafe-tostado",
            "https://www.ogrcafe.cl/cafe-tostado?page=2",
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
            translate_to_english=True
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

        # Extract all product URLs using the base class method
        all_product_url_el = soup.select('a.product-image')
        all_product_urls = []
        for el in all_product_url_el:
            if "No Disponible" not in el.text and el["href"] not in all_product_urls:
                all_product_urls.append(el["href"])

        excluded_pattern = []

        # Filter coffee products using base class method
        coffee_urls = []
        for url in all_product_urls:
            if not any(
                pattern in url for pattern in excluded_pattern
            ):
                coffee_urls.append(f"{self.base_url}{url}")

        logger.info(f"Found {len(coffee_urls)} coffee product URLs out of {len(all_product_urls)} total products")
        return coffee_urls
