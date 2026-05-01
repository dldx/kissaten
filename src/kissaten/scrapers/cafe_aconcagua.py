"""Café Aconcagua scraper implementation using Shopify JSON API."""

import logging
from typing import Any

from bs4 import BeautifulSoup

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="cafe-aconcagua",
    display_name="Café Aconcagua",
    roaster_name="Café Aconcagua",
    website="https://cafeaconcagua.cl",
    description="Coffee roastery based in Chile",
    requires_api_key=True,
    currency="CLP",  # Chilean Peso
    country="Chile",
    status="available",
)
class CafeAconcaguaScraper(ShopifyJsonScraper):
    """Scraper for Café Aconcagua (cafeaconcagua.cl) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Café Aconcagua scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Café Aconcagua",
            base_url="https://cafeaconcagua.cl",
            products_json_urls=[
                "https://cafeaconcagua.cl/collections/coleccion-tradicional/products.json",
                "https://cafeaconcagua.cl/collections/coleccion-prime/products.json",
                "https://cafeaconcagua.cl/collections/coleccion-alternativa/products.json",
                "https://cafeaconcagua.cl/collections/coleccion-especial/products.json",
                "https://cafeaconcagua.cl/collections/granos-alta-especialidad/products.json",
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
        # Filter out multi-packs and bundles
        excluded_products = ["pack-"]
        if any(excluded in url.lower() for excluded in excluded_products):
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
        """Override to ensure content is translated to English."""
        return await super()._extract_bean_with_ai(
            ai_extractor=ai_extractor,
            soup=soup,
            product_url=product_url,
            use_optimized_mode=use_optimized_mode,
            translate_to_english=True,
        )
