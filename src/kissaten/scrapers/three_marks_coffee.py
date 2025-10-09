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
            rate_limit_delay=1.5,
            max_retries=3,
            timeout=30.0,
        )
        from pathlib import Path

        self.output_dir = Path("data")

        self.ai_extractor = None
        try:
            from ..ai import CoffeeDataExtractor
            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
        except ImportError:
            logger.warning("AI extractor not available - AI extraction disabled")

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the store URLs to scrape
        """
        return [
            "https://threemarkscoffee.com/shop/",
        ]

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction."""
        if not product_urls:
            return []

        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        if self.ai_extractor:
            return await self.scrape_with_ai_extraction(
                extract_product_urls_function=get_new_product_urls,
                ai_extractor=self.ai_extractor,
                use_playwright=False,
            )
        else:
            logger.warning("AI extractor not available - cannot scrape new products without AI.")
            return []

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

        excluded_products = ["subscription", "gift-card", "curso-completo-barista-3", "-coffee-bags", "capsules"]
        # Use the base class method with WooCommerce-specific patterns
        product_urls = self.extract_product_urls_from_soup(
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
        # Filter out excluded products
        filtered_urls = []
        for url in product_urls:
            if not any(excluded in url.lower() for excluded in excluded_products):
                filtered_urls.append(url)
        return filtered_urls
