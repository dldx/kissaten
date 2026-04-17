"""Celsius Roasters scraper implementation with AI-powered extraction."""

import logging
from typing import Any

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .shopify_base import ShopifyJsonScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="passage-coffee",
    display_name="Passage Coffee",
    roaster_name="Passage Coffee",
    website="https://passagecoffee.com",
    description="Specialty coffee roaster based in Mitaka, Tokyo, Japan",
    requires_api_key=True,
    currency="JPY",
    country="Japan",
    status="available",
)
class PassageCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Passage Coffee (passagecoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Passage Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Passage Coffee",
            base_url="https://passagecoffee.com",
            products_json_urls=[
                "https://passagecoffee.com/en/collections/beans/products.json",
            ],
            scrape_product_pages=True,  # Translation usually needs the full page description
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup | Tag:
        """Clean up the product page HTML before AI extraction."""
        # Remove product carousel element
        product_carousels = soup.select("div[id*='product-recommendations']")
        for carousel in product_carousels:
            carousel.decompose()
        if product_el := soup.select("div.product-full-width"):
            return product_el[0]

        return soup

    async def _extract_bean_with_ai(
        self,
        ai_extractor: Any,
        soup: BeautifulSoup,
        product_url: str,
        use_optimized_mode: bool = False,
        translate_to_english: bool = False,
    ) -> CoffeeBean | None:
        """Override to ensure Japanese content is translated to English."""
        return await super()._extract_bean_with_ai(
            ai_extractor=ai_extractor,
            soup=soup,
            product_url=product_url,
            use_optimized_mode=use_optimized_mode,
            translate_to_english=True,
        )
