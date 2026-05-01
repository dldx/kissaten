"""Cafe Amor Perfecto scraper implementation using Shopify JSON API."""

import logging
from typing import Any

from bs4 import BeautifulSoup

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="cafe-amor-perfecto",
    display_name="Café Amor Perfecto",
    roaster_name="Café Amor Perfecto",
    website="https://cafeamorperfecto.com",
    description="Specialty coffee roaster based in Colombia",
    requires_api_key=True,
    currency="COP",
    country="Colombia",
    status="available",
)
class CafeAmorPerfectoScraper(ShopifyJsonScraper):
    """Scraper for Café Amor Perfecto using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Cafe Amor Perfecto scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Café Amor Perfecto",
            base_url="https://cafeamorperfecto.com",
            products_json_urls=[
                "https://cafeamorperfecto.com/collections/cafes-de-caficultor/products.json",
            ],
            scrape_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str | None:
        """Standardize the product URL and filter out non-coffee products."""
        # Filter patterns from original scraper
        excluded_patterns = [
            "coleccion",
            "organico",
            "tasting-set",
            "bundle",
            "gift-card",
            "accessories",
            "coffee-drip-bags",
            "-tea",
        ]
        url_lower = url.lower()
        if any(pattern in url_lower for pattern in excluded_patterns):
            return None

        # Standardize to direct /products/ URL
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
        """Override to ensure content is translated from Spanish to English."""
        return await super()._extract_bean_with_ai(
            ai_extractor=ai_extractor,
            soup=soup,
            product_url=product_url,
            use_optimized_mode=use_optimized_mode,
            translate_to_english=True,
        )
