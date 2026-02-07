"""Standout Coffee scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="standout",
    display_name="Standout Coffee",
    roaster_name="Standout Coffee AB",
    website="https://standoutcoffee.com",
    description="Swedish specialty coffee roaster from Stockholm",
    requires_api_key=True,
    currency="GBP",  # Website shows GBP pricing
    country="Sweden",
    status="available",
)
class StandoutCoffeeScraper(BaseScraper):
    """Scraper for Standout Coffee (standoutcoffee.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Standout Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Standout Coffee AB",
            base_url="https://www.standoutcoffee.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the store URLs for different coffee collections
        """
        return [
            "https://www.standoutcoffee.com/collections/featured-collection",
            "https://www.standoutcoffee.com/collections/specialty-coffee",
            "https://www.standoutcoffee.com/collections/competition-coffee",
            "https://www.standoutcoffee.com/collections/historic-coffee",
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
            use_playwright=False,  # Start with basic scraping, can enable if needed
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

        all_product_urls = []
        all_product_url_el = soup.select('a.full-unstyled-link[href*="/products/"]')
        for el in all_product_url_el:
            if "Sold out" not in el.parent.text:
                all_product_urls.append(self.base_url + el["href"])

        # Filter out equipment and non-coffee products
        filtered_urls = []
        for url in all_product_urls:
            if self._is_coffee_product_url(url):
                filtered_urls.append(url)

        return filtered_urls

    def _is_coffee_product_url(self, url: str) -> bool:
        """Filter out non-coffee products by URL patterns.

        Args:
            url: Product URL to check

        Returns:
            True if URL appears to be for coffee beans
        """
        # Exclude equipment and accessories
        excluded_patterns = [
            "meter",
            "digital",
            "water",
            "brewer",
            "grinder",
            "equipment",
            "accessories",
            "subscription",
            "gift",
            "merch",
            "capsule",
            "capsules",
            "the-standout-sample-box",
            "apax-lab-mineral-concentrates-standard-box-set",
            "standout-coffee-cap",
            "the-essential-a-seasonally-evolving-espresso-classic",
            "the-essential-espresso",
            "kinu-pour-over-replacement-burr",
            "sibarist"
        ]

        url_lower = url.lower()
        return not any(pattern in url_lower for pattern in excluded_patterns)
