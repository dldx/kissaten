"""Coffee Sakura scraper implementation with Shopify JSON extraction."""

import logging
from typing import Any

from ..schemas import CoffeeBean
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="coffee-sakura",
    display_name="Coffee Sakura",
    roaster_name="Coffee Sakura",
    website="https://shop.coffeesakura.co.jp",
    description="Specialty coffee roaster based in Japan",
    requires_api_key=True,
    currency="JPY",
    country="Japan",
    status="available",
)
class CoffeeSakuraScraper(ShopifyJsonScraper):
    """Scraper for Coffee Sakura (shop.coffeesakura.co.jp) using Shopify products.json."""

    def preprocess_product_url(self, url: str) -> str:
        """Ensure product URLs use the fixed /products/handle format, removing collections."""
        if "/products/" in url:
            handle = url.split("/products/")[-1]
            return f"{self.base_url}/products/{handle}"
        return url

    async def _fetch_all_shopify_products(self, products_json_url: str) -> list[dict[str, Any]]:
        """Fetch all products and force weights to 200g in the JSON metadata.

        This prevents Pydantic validation errors where prices for 1000g are
        calculated as being too low.
        """
        products = await super()._fetch_all_shopify_products(products_json_url)
        for product in products:
            for variant in product.get("variants", []):
                # Force weight to 200g in Shopify variant metadata
                variant["grams"] = 200
                variant["weight"] = 0.2
                variant["weight_unit"] = "kg"
        return products

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Override to ensure Japanese weights are correctly set to 200g."""
        bean.weight = 200
        return super().postprocess_extracted_bean(bean)

    async def _extract_bean_with_ai(
        self,
        ai_extractor: any,
        soup: any,
        product_url: str,
        use_optimized_mode: bool = False,
        translate_to_english: bool = True,
    ) -> CoffeeBean | None:
        """Override to ensure Japanese content is translated to English."""
        return await super()._extract_bean_with_ai(
            ai_extractor=ai_extractor,
            soup=soup,
            product_url=product_url,
            use_optimized_mode=use_optimized_mode,
            translate_to_english=True,  # Always translate Japanese to English
        )

    def __init__(self, api_key: str | None = None):
        """Initialize Coffee Sakura scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Coffee Sakura",
            base_url="https://shop.coffeesakura.co.jp",
            products_json_urls=[
                "https://shop.coffeesakura.co.jp/collections/coffeebeans200g/products.json",
            ],
            scrape_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

        # Exclude common non-coffee products
        self.exclude_slugs = [
            "gift-card",
            "subscription",
            "workshop",
            "tasting",
            "equipment",
            "accessories",
        ]
