"""Nomad Coffee scraper.

Spanish specialty coffee roaster based in Barcelona, offering single origin coffees
from various regions with espresso, filter, and competition roasts.
"""

import logging

from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="nomad-coffee",
    display_name="Nomad Coffee",
    roaster_name="Nomad Coffee",
    website="https://nomadcoffee.es",
    description="Spanish specialty coffee roaster from Barcelona offering "
    "espresso, filter, and competition roasts",
    requires_api_key=True,  # Using AI extraction for best results
    currency="EUR",
    country="Spain",
    status="available",
)
class NomadCoffeeScraper(BaseScraper):
    """Scraper for Nomad Coffee."""

    def __init__(self, api_key: str | None = None):
        """Initialize the scraper.

        Args:
            api_key: Optional API key for AI-powered extraction
        """
        super().__init__(
            roaster_name="Nomad Coffee",
            base_url="https://nomadcoffee.es",
            rate_limit_delay=1.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor (recommended for Shopify sites)
        self.ai_extractor = None
        try:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
        except ImportError:
            logger.warning("AI extractor not available - falling back to traditional extraction")

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the store URLs to scrape
        """
        return [
            "https://nomadcoffee.es/en/collections/coffee",
        ]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Nomad Coffee.

        Returns:
            List of CoffeeBean objects
        """
        # Use the AI-powered scraping workflow (recommended for Shopify sites)
        if self.ai_extractor:
            return await self.scrape_with_ai_extraction(
                extract_product_urls_function=self._extract_product_urls_from_store,
                ai_extractor=self.ai_extractor,
                use_playwright=False,  # Standard HTML scraping should work
            )

        # Fallback to traditional scraping if AI not available
        return await self._scrape_traditional()

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

        # Use the base class method with Shopify-specific patterns
        product_urls = self.extract_product_urls_from_soup(
            soup,
            # Shopify product URL pattern
            url_path_patterns=["/products/"],
            selectors=[
                # Shopify product link selectors
                'a[href*="/products/"]',
                ".product-item a",
                ".product-link",
                ".product-title a",
                "h3 a",  # Common pattern for product titles
                ".card-information a",
            ],
        )

        excluded_products = ["iced-latte-12-pack", "iced-coffee-12-pack", "test-roast"]

        # Filter out excluded products
        filtered_urls = [
            url for url in product_urls if not any(excluded in url.lower() for excluded in excluded_products)
        ]

        return filtered_urls
