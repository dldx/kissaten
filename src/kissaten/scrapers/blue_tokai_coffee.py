"""Blue Tokai Coffee scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="blue-tokai",
    display_name="Blue Tokai Coffee",
    roaster_name="Blue Tokai Coffee Roasters",
    website="https://bluetokaicoffee.com",
    description="Delhi-based specialty coffee roaster known for fresh single-origin and blends",
    requires_api_key=True,
    currency="INR",
    country="India",
    status="available",
)
class BlueTokaiCoffeeScraper(BaseScraper):
    """Scraper for Blue Tokai Coffee (bluetokaicoffee.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Blue Tokai Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Blue Tokai Coffee Roasters",
            base_url="https://bluetokaicoffee.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the store URLs - includes multiple pages
        """
        return [
            "https://bluetokaicoffee.com/collections/roasted-and-ground-coffee-beans",
            "https://bluetokaicoffee.com/collections/roasted-and-ground-coffee-beans?page=2",
        ]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Blue Tokai Coffee using AI extraction.

        Returns:
            List of CoffeeBean objects
        """
        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=self._extract_product_urls_from_store,
            ai_extractor=self.ai_extractor,
            use_playwright=False,  # Shopify sites usually work fine without Playwright
            use_optimized_mode=False,  # Standard mode should work for most products
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
        soup = soup.select("main.main-content")[0].select("div.shopify-section")[1]

        # Shopify-specific selectors for Blue Tokai Coffee
        custom_selectors = [
            'a[href*="/collections/"]',
            ".product-item a",
            ".product-link",
            "h3 a",  # Often used for product titles with links
            ".grid-item a",  # Common Shopify grid layout
            ".product-card a",  # Product card links
        ]

        product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/collections/"],
            selectors=custom_selectors,
        )

        # Filter out non-coffee products specific to Blue Tokai Coffee
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
            "equipment",
            "brewing-equipment",
            "merchandise",
            "merch",
            "accessories",
            "filter",
            "dripper",
            "carafe",
            "mug",
            "cup",
            "grinder",
            "kettle",
            "scale",
            "gift-card",
            "gift-voucher",
            "book",
            "tshirt",
            "tee",
            "hoodie",
            "apparel",
            "capsules",  # Nespresso-style capsules, not coffee beans
            "pods",
            "easy-pour",  # Pre-ground sachets, not whole beans
            "cold-brew-cans",  # Pre-made drinks, not coffee beans
            "sampler",
        ]

        url_lower = url.lower()
        for pattern in excluded_patterns:
            if pattern in url_lower:
                return False

        return True
