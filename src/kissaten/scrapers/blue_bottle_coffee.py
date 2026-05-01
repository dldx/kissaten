"""Blue Bottle Coffee Japan scraper implementation using Shopify JSON API."""

import logging
from typing import Any

from bs4 import BeautifulSoup

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="blue-bottle",
    display_name="Blue Bottle Coffee",
    roaster_name="Blue Bottle Coffee",
    website="https://store.bluebottlecoffee.jp",
    description="Premium specialty coffee roasters from California with Japan operations",
    requires_api_key=True,
    currency="JPY",
    country="Japan",
    status="available",
)
class BlueBottleCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Blue Bottle Coffee Japan (store.bluebottlecoffee.jp) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Blue Bottle Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Blue Bottle Coffee",
            base_url="https://store.bluebottlecoffee.jp",
            products_json_urls=[
                "https://store.bluebottlecoffee.jp/collections/blend/products.json",
                "https://store.bluebottlecoffee.jp/collections/single-origin/products.json",
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
        excluded_patterns = [
            "dripper",
            "filter",
            "mill",
            "grinder",
            "mug",
            "cup",
            "glass",
            "tumbler",
            "kit",
            "starter",
            "equipment",
            "brewing",
            "accessories",
            "merchandise",
            "apparel",
            "shirt",
            "tote",
            "bag",
            "subscription",
            "granola",
        ]
        url_lower = url.lower()
        if any(pattern in url_lower for pattern in excluded_patterns):
            return None

        # Standardize to direct products/ URL structure
        if "/products/" in url:
            handle = url.split("/products/")[-1]
            # Ensure the URL matches the canonical pattern provided
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
        """Override to ensure Japanese content is translated to English."""
        bean = await super()._extract_bean_with_ai(
            ai_extractor=ai_extractor,
            soup=soup,
            product_url=product_url,
            use_optimized_mode=use_optimized_mode,
            translate_to_english=True,
        )

        if bean:
            # Further post-extraction filtering
            name_lower = (bean.name or "").lower()
            if any(p in name_lower for p in ["ground", "selection"]):
                logger.info(f"Excluding product by name pattern: {bean.name}")
                return None

        return bean
