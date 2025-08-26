"""Special Guests Coffee scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="special-guests",
    display_name="Special Guests Coffee",
    roaster_name="Special Guests Coffee",
    website="https://specialguestscoffee.com",
    description="London-based specialty coffee roaster known for rare and exceptional coffees",
    requires_api_key=True,
    currency="GBP",
    country="UK",
    status="available",
)
class SpecialGuestsCoffeeScraper(BaseScraper):
    """Scraper for Special Guests Coffee (specialguestscoffee.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Special Guests Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Special Guests Coffee",
            base_url="https://specialguestscoffee.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the store URL
        """
        return ["https://specialguestscoffee.com/collections/coffee"]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Special Guests Coffee using AI extraction.

        Returns:
            List of CoffeeBean objects
        """
        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=self._extract_product_urls_from_store,
            ai_extractor=self.ai_extractor,
            use_playwright=False,
            batch_size=2,
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

        # Shopify-specific selectors for Special Guests Coffee
        custom_selectors = [
            'a[href*="/products/"]',
            ".product-item a",
            ".product-link",
            "h3 a",  # Often used for product titles with links
        ]

        product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/products/"],
            selectors=custom_selectors,
        )

        # Filter out non-coffee products specific to Special Guests Coffee
        filtered_urls = []
        for url in product_urls:
            if self._is_coffee_product_url(url):
                filtered_urls.append(url)

        return filtered_urls

    def _is_coffee_product_url(self, url: str) -> bool:
        """Filter out non-coffee products based on URL patterns."""
        # Exclude equipment, accessories, and subscriptions that aren't individual coffee beans
        excluded_patterns = [
            "subscription",
            "dripper",
            "carafe",
            "spoon",
            "jumper",
            "tumbler",
            "filter",
            "equipment",
            "merch",
            "accessories",
        ]

        url_lower = url.lower()
        for pattern in excluded_patterns:
            if pattern in url_lower:
                return False

        return True
