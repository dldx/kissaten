"""KillBean Coffee scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="killbean",
    display_name="KillBean Coffee",
    roaster_name="KillBean",
    website="killbean.co.uk",
    description="UK specialty coffee roaster based in London",
    requires_api_key=True,
    currency="GBP",
    country="UK",
    status="available",
)
class KillBeanScraper(BaseScraper):
    """Scraper for KillBean Coffee (killbean.co.uk) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize KillBean scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="KillBean",
            base_url="https://killbean.co.uk",
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
        return ["https://killbean.co.uk/shop"]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from KillBean Coffee store using AI extraction.

        Returns:
            List of CoffeeBean objects
        """
        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=self._extract_product_urls_from_store,
            ai_extractor=self.ai_extractor,
            use_playwright=True,
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

        # Custom selectors for KillBean Coffee based on the website structure
        # Looking for coffee product links, excluding merch like caps and t-shirts
        custom_selectors = [
            'a[href*="/shop/p/"]',
            ".product-item a",
            ".collection-item a",
            'a[class*="product"]',
        ]

        # Extract all product URLs using the base class method
        all_product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/shop/p/"],
            selectors=custom_selectors,
        )

        # Filter out non-coffee products (merch, equipment, etc.)
        coffee_urls = []
        for url in all_product_urls:
            # Skip obvious non-coffee items based on URL patterns
            if any(pattern in url.lower() for pattern in [
                "cap", "t-shirt", "tshirt", "shirt", "merch", "dosing-cup",
                "brewing-pad", "brewingpad", "v60", "equipment", "accessories"
            ]):
                logger.debug(f"Skipping non-coffee product: {url}")
                continue

            coffee_urls.append(url)

        logger.info(f"Found {len(coffee_urls)} coffee product URLs out of {len(all_product_urls)} total products")
        return coffee_urls
