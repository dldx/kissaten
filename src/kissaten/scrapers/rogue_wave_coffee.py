"""Rogue Wave Coffee scraper implementation with AI-powered extraction."""

import logging

from bs4 import BeautifulSoup

from ..schemas import CoffeeBean
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="rogue-wave-coffee",
    display_name="Rogue Wave Coffee",
    roaster_name="Rogue Wave Coffee",
    website="https://roguewavecoffee.ca",
    description="Canadian specialty coffee roaster based in Edmonton, "
    "offering single origins and unique processing methods",
    requires_api_key=True,
    currency="CAD",
    country="Canada",
    status="available",
)
class RogueWaveCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Rogue Wave Coffee using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Rogue Wave Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Rogue Wave Coffee",
            base_url="https://roguewavecoffee.ca",
            products_json_urls=[
                "https://roguewavecoffee.ca/collections/coffee/products.json",
            ],
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
            scrape_product_pages=True,
        )

        # Exclude non-coffee products
        self.exclude_slugs = [
            "roaster-surprise",
            "roaster surprise",
            "surprise",
            "roasters-club",
            "/mhw",
            "origami",
            "kettle",
            "brewista",
            "custom-coffee-beans",
            "april-hybrid",
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "accessory",
            "merchandise",
            "ceramic",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Rogue Wave URLs by removing collection segments."""
        if "/collections/" in url and "/products/" in url:
            # Extract handle from localized or collection URL
            # e.g., https://roguewavecoffee.ca/collections/coffee/products/slug
            # -> https://roguewavecoffee.ca/products/slug
            try:
                handle = url.split("/products/")[-1].split("?")[0]
                return f"{self.base_url}/products/{handle}"
            except Exception:
                return url
        return url

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Filter the product page HTML to only include the product info wrapper."""
        info_wrapper = soup.select_one("div.product__info-wrapper")
        if info_wrapper:
            # Create a new minimal soup with just the info wrapper
            # This follows the pattern expected by ShopifyJsonScraper's _extract_bean_with_ai
            return BeautifulSoup(str(info_wrapper), "html.parser")
        return soup

    async def _extract_bean_with_ai(
        self,
        ai_extractor,
        soup: BeautifulSoup,
        product_url: str,
        use_optimized_mode: bool = False,
        translate_to_english: bool = False,
    ) -> CoffeeBean | None:
        """Extract bean data from the preprocessed soup."""
        return await super()._extract_bean_with_ai(
            ai_extractor,
            soup,
            product_url,
            use_optimized_mode=use_optimized_mode,
            translate_to_english=translate_to_english,
        )
