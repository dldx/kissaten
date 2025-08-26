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

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Hola Coffee.

        Returns:
            List of CoffeeBean objects
        """
        # Use the AI-powered scraping workflow (recommended for Shopify sites)
        if self.ai_extractor:
            return await self.scrape_with_ai_extraction(
                extract_product_urls_function=self._extract_product_urls_from_store,
                ai_extractor=self.ai_extractor,
                use_playwright=False,  # Standard HTML scraping should work for this site
                batch_size=3,  # Conservative batch size to respect rate limits
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

    async def _scrape_traditional(self) -> list[CoffeeBean]:
        """Traditional scraping fallback (for sites that don't need AI extraction).

        This is a simplified fallback - the AI extraction above is preferred.
        """
        session = self.start_session()
        coffee_beans = []

        try:
            store_urls = self.get_store_urls()

            for store_url in store_urls:
                logger.info(f"Scraping store page: {store_url}")
                soup = await self.fetch_page(store_url)

                if not soup:
                    logger.error(f"Failed to fetch store page: {store_url}")
                    continue

                session.pages_scraped += 1

                # Extract product URLs
                product_urls = await self._extract_product_urls_from_store(store_url)
                logger.info(f"Found {len(product_urls)} product URLs on {store_url}")

                # Since this is a fallback, we'll just collect the URLs
                # In practice, the AI extractor above should be used
                for product_url in product_urls:
                    logger.debug(f"Would extract from: {product_url}")

            session.beans_found = len(coffee_beans)
            session.beans_processed = len(coffee_beans)
            self.end_session(success=True)

        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            session.add_error(f"Scraping error: {e}")
            self.end_session(success=False)
            raise

        return coffee_beans
