"""Artisan Roast Chile scraper implementation with Shopify JSON extraction."""

import logging

from ..schemas import CoffeeBean
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="artisan-roast-cl",
    display_name="Artisan Roast Chile",
    roaster_name="Artisan Roast Chile",
    website="https://shop.artisanroast.cl",
    description="Chilean specialty coffee roaster focused on circular coffee practices",
    requires_api_key=True,  # Use AI extraction for this Spanish-language site
    currency="CLP",  # Chilean Peso
    country="Chile",
    status="available",
)
class ArtisanRoastScraper(ShopifyJsonScraper):
    """Scraper for Artisan Roast Chile coffee roaster using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Artisan Roast Chile scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Artisan Roast Chile",
            base_url="https://shop.artisanroast.cl",
            products_json_urls=[
                "https://shop.artisanroast.cl/collections/origenes/products.json",
                "https://shop.artisanroast.cl/collections/blends/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=1.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Initialize AI extractor for this Spanish-language site
        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def _extract_bean_with_ai(
        self,
        ai_extractor: any,
        soup: any,
        product_url: str,
        use_optimized_mode: bool = False,
        translate_to_english: bool = True,
    ) -> CoffeeBean | None:
        """Override to ensure Spanish content is translated to English."""
        return await super()._extract_bean_with_ai(
            ai_extractor=ai_extractor,
            soup=soup,
            product_url=product_url,
            use_optimized_mode=use_optimized_mode,
            translate_to_english=True,  # Always translate Spanish to English
        )
