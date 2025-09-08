"""Bluebird Coffee Roastery scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="bluebird-coffee",
    display_name="Bluebird Coffee Roastery",
    roaster_name="Bluebird Coffee Roastery",
    website="https://www.bluebirdcoffeeroastery.co.za",
    description="South African specialty coffee roaster offering single origins and blends",
    requires_api_key=True,
    currency="ZAR",
    country="South Africa",
    status="available",
)
class BluebirdCoffeeScraper(BaseScraper):
    """Scraper for Bluebird Coffee Roastery (bluebirdcoffeeroastery.co.za) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Bluebird Coffee Roastery scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Bluebird Coffee Roastery",
            base_url="https://www.bluebirdcoffeeroastery.co.za",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the coffee collection URLs
        """
        return [
            "https://www.bluebirdcoffeeroastery.co.za/product-tag/single-origin/",
            "https://www.bluebirdcoffeeroastery.co.za/special-releases/",
            "https://www.bluebirdcoffeeroastery.co.za/product-tag/espresso-blend/",
        ]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Bluebird Coffee Roastery using AI extraction.

        Returns:
            List of CoffeeBean objects
        """
        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=self._extract_product_urls_from_store,
            ai_extractor=self.ai_extractor,
            use_playwright=True,
            use_optimized_mode=True
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

        # Get all product URLs using the base class method
        product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/product/"],
            selectors=[
                # WooCommerce product link selectors
                'a[href*="/product/"]',
                '.woocommerce-LoopProduct-link',
                '.product-item a',
                '.product-link',
                '.wc-block-grid__product a',
                # Bluebird specific selectors based on HTML structure
                '.product a',
                '.product-wrapper a',
            ],
        )

        # Filter out excluded products (subscriptions and non-coffee items)
        excluded_products = [
            "subscription",  # Coffee subscriptions
            "coffee-subscription",  # Coffee subscriptions
            "house-blend-subscription",  # Espresso blend subscriptions
        ]

        filtered_urls = []
        for url in product_urls:
            # Check if any excluded product identifier is in the URL
            if not any(excluded in url for excluded in excluded_products):
                filtered_urls.append(url)

        return filtered_urls
