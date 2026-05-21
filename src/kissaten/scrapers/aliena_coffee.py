"""Aliena Coffee Roasters scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="aliena",
    display_name="Aliena Coffee Roasters",
    roaster_name="Aliena Coffee Roasters",
    website="https://caffealiena.com",
    description="Specialty coffee roaster based in Rome",
    requires_api_key=True,
    currency="EUR",  # Website shows EUR pricing
    country="Italy",
    status="available",
)
class AlienaCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Aliena Coffee Roasters (caffealiena.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Aliena Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Aliena Coffee Roasters",
            base_url="https://caffealiena.com",
            products_json_urls=[
                "https://caffealiena.com/collections/frontpage/products.json",
            ],
            scrape_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

        # Exclude equipment and accessories
        self.exclude_slugs = [
            "cold-brew",
            "gift-card",
            "subscription",
        ]

    def preprocess_product_url(self, url: str) -> str:
        """Remove collection segments for canonical URLs."""
        return url.replace("/collections/frontpage", "")

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        self.store_currency = "EUR"  # Ensure currency is set to EUR for this scraper
        return super().postprocess_extracted_bean(bean)

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using Shopify JSON context.

        Args:
            product_urls: List of URLs for new products

        Returns:
            List of newly scraped CoffeeBean objects
        """
        if not product_urls:
            return []

        # Create a simple function that returns the product urls
        async def get_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_product_urls,
            ai_extractor=self.ai_extractor,
            use_optimized_mode=True,
        )
