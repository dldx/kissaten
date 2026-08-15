"""Bonanza scraper implementation with Shopify JSON extraction."""

import logging
from typing import Any

from bs4 import BeautifulSoup

from ..schemas import CoffeeBean
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="bonanza",
    display_name="Bonanza",
    roaster_name="Bonanza",
    website="https://bonanzacoffee.de",
    description="Berlin-based specialty coffee roaster (Bonanza Coffee Roasters), known for "
    "highly traceable single-origin coffees and its long-running coffee roastery since 2006.",
    requires_api_key=True,
    currency="EUR",
    country="Germany",
    status="available",
)
class BonanzaScraper(ShopifyJsonScraper):
    """Scraper for Bonanza (bonanzacoffee.de) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Bonanza scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Bonanza",
            base_url="https://bonanzacoffee.de",
            products_json_urls=["https://bonanzacoffee.de/collections/coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude non-bean products (sets/boxes, subscription, equipment, merch, etc.).
        # The curated /collections/coffee products.json only exposes coffee-family
        # items, but these keywords keep future additions out of the bean index.
        self.exclude_slugs = [
            "set",
            "box",
            "sample",
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "sampler",
            "taster-pack",
            "apparel",
            "mug",
            "tumbler",
            "hoodie",
            "tshirt",
            "capsules",
            "pods",
            "cold-brew-cans",
            "easy-pour",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Bonanza product URLs to /products/<handle>.

        Shopify builds product URLs under the collection path, but Bonanza's
        canonical product pages live at /products/<handle> without a
        collection segment. Strip it so all products share the real URL.
        """
        if "/collections/" in url and "/products/" in url:
            handle = url.split("/products/", 1)[1]
            return f"{self.base_url}/products/{handle}"
        return url

    async def _extract_bean_with_ai(
        self,
        ai_extractor: Any,
        soup: BeautifulSoup,
        product_url: str,
        use_optimized_mode: bool = False,
        translate_to_english: bool = True,
    ) -> CoffeeBean | None:
        """Override to ensure German content is translated to English."""
        return await super()._extract_bean_with_ai(
            ai_extractor=ai_extractor,
            soup=soup,
            product_url=product_url,
            use_optimized_mode=use_optimized_mode,
            translate_to_english=True,  # Always translate German to English
        )
