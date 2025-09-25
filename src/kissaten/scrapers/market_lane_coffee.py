""" Market Lane Coffee scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="market-lane-coffee",
    display_name="Market Lane Coffee",
    roaster_name="Market Lane Coffee",
    website="https://marketlane.com.au",
    description="Specialty coffee roaster based in Melbourne, Australia",
    requires_api_key=True,
    currency="AUD",
    country="Australia",
    status="available",
)
class MarketLaneCoffeeScraper(BaseScraper):
    """Scraper for Frukt Coffee with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Market Lane Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Market Lane Coffee",
            base_url="https://marketlane.com.au",
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
        return ["https://marketlane.com.au/pages/coffee"]


    def _get_excluded_url_patterns(self) -> list[str]:
        """Get list of URL patterns to exclude from product URLs.

        Returns:
            List of URL patterns that indicate non-coffee products
        """
        return ["tasting-set", "bundle",  "gift-card", "accessories", "coffee-drip-bags", "-tea"]

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
        all_product_url_el = soup.select('a[href*="/products/"]')
        for el in all_product_url_el:
            all_product_urls.append(f"https://marketlane.com.au{el['href']}")

        # Filter coffee products using base class method
        excluded_patterns = []
        coffee_urls = []
        for url in all_product_urls:
            if self.is_coffee_product_url(url, required_path_patterns=["/products/"]) and not any(
                pattern in url for pattern in excluded_patterns
            ):
                coffee_urls.append(url)

        logger.info(f"Found {len(coffee_urls)} coffee product URLs out of {len(all_product_urls)} total products")
        return list(set(coffee_urls))
