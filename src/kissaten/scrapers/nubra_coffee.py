"""Nubra Coffee Roasters scraper.

Spanish specialty coffee roaster based in Spain, offering single origin coffees
from Colombia, Ethiopia, Kenya, Nicaragua, and Panama.
"""

import logging

from ..schemas import CoffeeBean
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="nubra-coffee",
    display_name="Nubra Coffee Roasters",
    roaster_name="Nubra Coffee Roasters",
    website="https://nubra.coffee",
    description="Spanish specialty coffee roaster offering single origin coffees "
    "from Central and South America, Africa",
    requires_api_key=True,  # Using AI extraction for best results
    currency="EUR",
    country="Spain",
    status="available",
)
class NubraCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Nubra Coffee Roasters."""

    def __init__(self, api_key: str | None = None):
        """Initialize the scraper.

        Args:
            api_key: Optional API key for AI-powered extraction
        """
        super().__init__(
            roaster_name="Nubra Coffee Roasters",
            base_url="https://nubra.coffee",
            products_json_urls=["https://nubra.coffee/en/collections/all/products.json"],
            use_optimized_mode=True,
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

    def preprocess_product_url(self, url: str) -> str:
        """Standardize the product URL and ensure it uses the correct localized path.

        Example: https://nubra.coffee/en/collections/all/products/colombia-jonathan-gasca
        becomes: https://nubra.coffee/en/products/colombia-jonathan-gasca
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1]
            return f"{self.base_url}/en/products/{handle}"

        return url

    async def _scrape_new_products(self, product_urls: list[str], use_optimized_mode: bool = False) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction.

        Args:
            product_urls: List of URLs for new products
            use_optimized_mode: Whether to use optimized Shopify extraction mode

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
            translate_to_english=True,  # The site is in Spanish
            use_optimized_mode=use_optimized_mode or self.use_optimized_mode,
        )
