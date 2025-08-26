"""Three Marks Coffee scraper.

Spanish specialty coffee roaster offering single origin coffees
from various regions including Brazil, Mexico, Ethiopia, Rwanda, and more.
"""

import logging

from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="three-marks-coffee",
    display_name="Three Marks Coffee",
    roaster_name="Three Marks Coffee",
    website="https://threemarkscoffee.com",
    description="Spanish specialty coffee roaster offering single origin and "
    "seasonal coffee marks from around the world",
    requires_api_key=True,  # Using AI extraction for best results
    currency="EUR",
    country="Spain",
    status="available",
)
class ThreeMarksCoffeeScraper(BaseScraper):
    """Scraper for Three Marks Coffee."""

    def __init__(self, api_key: str | None = None):
        """Initialize the scraper.

        Args:
            api_key: Optional API key for AI-powered extraction
        """
        super().__init__(
            roaster_name="Three Marks Coffee",
            base_url="https://threemarkscoffee.com",
            rate_limit_delay=1.5,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor (recommended for WooCommerce sites)
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
            "https://threemarkscoffee.com/shop/",
        ]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Three Marks Coffee.

        Returns:
            List of CoffeeBean objects
        """
        # Use the AI-powered scraping workflow (recommended for WooCommerce sites)
        if self.ai_extractor:
            return await self.scrape_with_ai_extraction(
                extract_product_urls_function=self._extract_product_urls_from_store,
                ai_extractor=self.ai_extractor,
                use_playwright=False,  # Standard HTML scraping should work
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

        # Use the base class method with WooCommerce-specific patterns
        return self.extract_product_urls_from_soup(
            soup,
            # WooCommerce product URL pattern
            url_path_patterns=["/producto/"],
            selectors=[
                # WooCommerce product link selectors
                'a[href*="/producto/"]',
                ".woocommerce-LoopProduct-link",
                ".product-link",
                ".wc-block-grid__product a",
                "h2 a",  # Common pattern for product titles
                ".product-title a",
            ],
        )

    async def _scrape_traditional(self) -> list[CoffeeBean]:
        """Traditional scraping fallback.
        
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
