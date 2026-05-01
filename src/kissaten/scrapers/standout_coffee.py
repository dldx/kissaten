"""Standout Coffee scraper implementation with AI-powered extraction."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="standout",
    display_name="Standout Coffee",
    roaster_name="Standout Coffee AB",
    website="https://standoutcoffee.com",
    description="Swedish specialty coffee roaster from Stockholm",
    requires_api_key=True,
    currency="GBP",  # Website shows GBP pricing
    country="Sweden",
    status="available",
)
class StandoutCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Standout Coffee (standoutcoffee.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Standout Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Standout Coffee AB",
            base_url="https://www.standoutcoffee.com",
            products_json_urls=[
                "https://www.standoutcoffee.com/collections/all/products.json",
            ],
            scrape_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

        # Exclude equipment and accessories
        self.exclude_slugs = [
            "meter",
            "digital",
            "water",
            "brewer",
            "grinder",
            "equipment",
            "accessories",
            "subscription",
            "gift",
            "merch",
            "capsule",
            "capsules",
            "sample-box",
            "apax-lab",
            "coffee-cap",
            "the-essential",
            "the-essential",
            "-burr",
            "sibarist",
            # New exclusions based on products.json
            "aeropress",
            "autocomb",
            "spiritello",
            "hario",
            "nucleus",
            "orea",
            "kinu",
            "barista-hustle",
            "dripper",
            "filter",
            "scale",
            "pitcher",
            "tamper",
            "machine",
            "concentrates",
            "mineral",
            "gift-card",
            "jar",
        ]

    def preprocess_product_url(self, url: str) -> str:
        """Remove collection segments for canonical URLs."""
        return url.replace("/collections/all", "")

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Override to ensure weights are correctly set to 250g."""
        if bean.weight == 311:
            bean.weight = 250
        for option in bean.price_options:
            if option.weight == 311:
                option.weight = 250
            if option.weight == 1007:
                option.weight = 1000
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

        # Use the optimized Shopify JSON mode since we don't need to scrape individual pages
        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_product_urls,
            ai_extractor=self.ai_extractor,
            use_optimized_mode=True,
        )
