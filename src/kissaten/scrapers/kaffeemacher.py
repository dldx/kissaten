"""Kaffeemacher scraper implementation with Shopify JSON extraction."""

import logging
from typing import Any

from bs4 import BeautifulSoup

from ..schemas import CoffeeBean
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="kaffeemacher",
    display_name="kaffeemacher",
    roaster_name="kaffeemacher",
    website="https://kaffeemacher.de",
    description="Swiss/German specialty coffee roaster focused on roasting with sensitivity and care based in Basel, Switzerland.",
    requires_api_key=True,
    currency="EUR",
    country="Switzerland",
    status="available",
)
class KaffeemacherScraper(ShopifyJsonScraper):
    """Scraper for Kaffeemacher (kaffeemacher.de) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Kaffeemacher scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="kaffeemacher",
            base_url="https://kaffeemacher.de",
            products_json_urls=[
                "https://kaffeemacher.de/en/collections/kaffee/products.json",
                "https://kaffeemacher.de/en/collections/espresso-auswahl/products.json",
                "https://kaffeemacher.de/en/collections/entkoffeinierter-kaffee/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude non-coffee products (subscriptions, gift cards, gift sets, equipment, etc.)
        self.exclude_slugs = [
            "subscription",
            "-abo",
            "gift-card",
            "gift",
            "geschenkset",
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
        """Standardize Kaffeemacher product URLs to /en/products/<handle>.

        Shopify builds product URLs under each collection path; we strip the
        collection segment so that all products share a single canonical URL,
        regardless of which collection they appear in.
        """
        if "/collections/" in url and "/products/" in url:
            handle = url.split("/products/", 1)[1]
            return f"{self.base_url}/en/products/{handle}"
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
