"""Bugan Coffee Lab scraper implementation with AI-powered extraction."""

import logging
from typing import Any

from bs4 import BeautifulSoup

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="bugan",
    display_name="Bugan Coffee Lab",
    roaster_name="Bugan Coffee Lab",
    website="https://bugancoffeelab.com",
    description="Italian specialty coffee roaster and lab with locations in Milan and Bergamo",
    requires_api_key=True,
    currency="EUR",
    country="Italy",
    status="available",
)
class BuganCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Bugan Coffee Lab (bugancoffeelab.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Bugan Coffee Lab scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Bugan Coffee Lab",
            base_url="https://bugancoffeelab.com",
            products_json_urls=[
                "https://bugancoffeelab.com/en/collections/specialty-coffee/products.json",
            ],
            scrape_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str | None:
        """Standardize the product URL and filter out excluded products."""
        # Check for excluded products
        excluded_products = [
            "cold-brew",
            "cold brew",
            "box-degustazione",
            "box-di-degustazione",
            "degustazione",
        ]
        if any(excluded in url.lower() for excluded in excluded_products):
            return None

        # Standardize structure
        if "/products/" in url and "/collections/" not in url:
            return url.replace("/products/", "/en/collections/specialty-coffee/products/")
        return url

    async def _extract_bean_with_ai(
        self,
        ai_extractor: Any,
        soup: BeautifulSoup,
        product_url: str,
        use_optimized_mode: bool = False,
        translate_to_english: bool = False,
    ) -> CoffeeBean | None:
        """Override to ensure Italian content is translated to English."""
        return await super()._extract_bean_with_ai(
            ai_extractor=ai_extractor,
            soup=soup,
            product_url=product_url,
            use_optimized_mode=use_optimized_mode,
            translate_to_english=True,
        )
