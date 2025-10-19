"""MOK coffee scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="mok-coffee",
    display_name="MOK Coffee",
    roaster_name="MOK Coffee",
    website="https://mokcoffee.be",
    description="Specialty coffee roaster based in Brussels, Belgium",
    requires_api_key=True,
    currency="EUR",
    country="Belgium",
    status="available",
)
class MOKCoffeeScraper(BaseScraper):
    """Scraper for MOK Coffee with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize MOK Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="MOK Coffee",
            base_url="https://mokcoffee.be",
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
        return ["https://mokcoffee.be/collections/coffee"]

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
        all_product_url_el = soup.select('a.product[href*="/products/"]')
        all_product_urls = []
        for el in all_product_url_el:
            all_product_urls.append(el["href"])

        excluded_pattern = ["xmas", "voucher"]

        # Filter coffee products using base class method
        coffee_urls = []
        for url in all_product_urls:
            if self.is_coffee_product_url(url, required_path_patterns=["/products/"]) and not any(
                pattern in url for pattern in excluded_pattern
            ):
                coffee_urls.append(f"{self.base_url}{url}")

        logger.info(f"Found {len(coffee_urls)} coffee product URLs out of {len(all_product_urls)} total products")
        return coffee_urls
