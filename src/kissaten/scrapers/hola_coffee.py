"""Hola Coffee Roasters scraper.

Spanish specialty coffee roaster based in Madrid, offering single origin coffees
from around the world with detailed tasting notes and brewing recipes.
"""

import logging

from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="hola-coffee",
    display_name="Hola Coffee Roasters",
    roaster_name="Hola Coffee Roasters",
    website="https://hola.coffee",
    description="Spanish specialty coffee roaster based in Madrid offering "
    "single origin coffees with detailed tasting notes and brewing recipes",
    requires_api_key=True,  # Using AI extraction for best results
    currency="GBP",  # They show prices in GBP on their English site
    country="Spain",
    status="available",
)
class HolaCoffeeScraper(BaseScraper):
    """Scraper for Hola Coffee Roasters."""

    def __init__(self, api_key: str | None = None):
        """Initialize the scraper.

        Args:
            api_key: Optional API key for AI-powered extraction
        """
        super().__init__(
            roaster_name="Hola Coffee Roasters",
            base_url="https://hola.coffee",
            rate_limit_delay=1.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor (recommended for complex Shopify sites)
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
            "https://hola.coffee/en-gb/collections/cafe-en-grano-o-molido",
            # The site may have pagination, but the AI extractor should handle this automatically
            # by following pagination links if needed
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

        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=False,
            translate_to_english=True,  # Translate Spanish content to English
        )

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
        return self.extract_product_urls_from_soup(
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
                ".grid-product__title a",  # Another common Shopify pattern
            ],
        )
