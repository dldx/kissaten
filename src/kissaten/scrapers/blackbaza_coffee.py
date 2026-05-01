"""Back Baza Coffee scraper implementation using Shopify JSON API."""

import logging
from typing import Any

from bs4 import BeautifulSoup

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="blackbaza-coffee",
    display_name="Black Baza Coffee",
    roaster_name="Black Baza Coffee",
    website="https://www.blackbazacoffee.com",
    description="Specialty coffee roaster with a focus on sustainable practices based in India.",
    requires_api_key=True,
    currency="INR",
    country="India",
    status="available",
)
class BlackBazaCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Black Baza Coffee with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Black Baza Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Black Baza Coffee",
            base_url="https://www.blackbazacoffee.com",
            products_json_urls=[
                "https://www.blackbazacoffee.com/collections/coffee/products.json",
            ],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str | None:
        """Standardize the product URL and filter out excluded products."""
        # Filter out excluded products
        excluded_products = ["sampler-pack", "bundle"]
        if any(excluded in url.lower() for excluded in excluded_products):
            return None

        # Standardize to /products/ structure (removing collection segments)
        if "/products/" in url:
            handle = url.split("/products/")[-1]
            return f"{self.base_url}/products/{handle}"

        return url

    async def _extract_bean_with_ai(
        self,
        ai_extractor: Any,
        soup: BeautifulSoup,
        product_url: str,
        use_optimized_mode: bool = False,
        translate_to_english: bool = False,
    ) -> CoffeeBean | None:
        """Extract bean data and take a screenshot of the product page."""
        # Capture screenshot for internal validation
        await self.take_screenshot(product_url)

        # Call base extraction
        return await super()._extract_bean_with_ai(
            ai_extractor=ai_extractor,
            soup=soup,
            product_url=product_url,
            use_optimized_mode=use_optimized_mode,
            translate_to_english=translate_to_english,
        )
