"""Process Coffee scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="frukt",
    display_name="Frukt Coffee Roasters",
    roaster_name="Frukt Coffee",
    website="https://frukt.coffee",
    description="Specialty coffee roaster based in Turku, Finland",
    requires_api_key=True,
    currency="EUR",
    country="Finland",
    status="available",
)
class FruktCoffeeScraper(BaseScraper):
    """Scraper for Frukt Coffee with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Frukt Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Frukt Coffee Roasters",
            base_url="https://frukt.coffee",
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
        return ["https://www.frukt.coffee/pages/store"]


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
        collection_grids = soup.select('div.site-box-container')[1:4]
        all_product_urls = []
        # Extract all product URLs
        for grid in collection_grids:
            all_product_url_el = grid.select('a[href*="/products/"]')
            for el in all_product_url_el:
                if not "Sold out" in el.text:
                    all_product_urls.append(f"https://frukt.coffee{el['href']}")

        # Filter coffee products using base class method
        excluded_patterns = ["tasting-set", "gift-card", "accessories", "merch"]
        coffee_urls = []
        for url in all_product_urls:
            if self.is_coffee_product_url(url, required_path_patterns=["/products/"]) and not any(
                pattern in url for pattern in excluded_patterns
            ):
                coffee_urls.append(url)

        logger.info(f"Found {len(coffee_urls)} coffee product URLs out of {len(all_product_urls)} total products")
        return coffee_urls
