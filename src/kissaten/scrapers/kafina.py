"""Kafina scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="kafina",
    display_name="Kafina",
    roaster_name="Kafina",
    website="https://kafinacoffee.fr",
    description="French specialty coffee roaster offering SCA-scored single "
    "origins and limited-edition co-fermented coffees",
    requires_api_key=True,
    currency="EUR",
    country="France",
    status="experimental",
)
class KafinaScraper(ShopifyJsonScraper):
    """Scraper for Kafina (kafinacoffee.fr) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Kafina scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Kafina",
            base_url="https://kafinacoffee.fr",
            products_json_urls=["https://kafinacoffee.fr/collections/produits-dispoibles/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude the drip-bag product; the available-products collection is
        # otherwise all roasted beans (equipment/subscriptions live elsewhere).
        self.exclude_slugs = [
            "capsulas",
        ]

        # Pin the home-market currency: Shopify Markets can geo-convert prices
        # for datacenter IPs; cart.js from the home market reports EUR.
        self.store_currency = "EUR"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize product URLs to the canonical /products/<handle> form.

        The site's product sitemap uses the no-collection URL form.
        """
        return re.sub(r"/collections/[^/]+/products/", "/products/", url)

    async def _extract_bean_with_ai(
        self,
        ai_extractor,
        soup,
        product_url,
        use_optimized_mode: bool = False,
        translate_to_english: bool = True,
    ):
        """Override to ensure French product content is translated to English."""
        return await super()._extract_bean_with_ai(
            ai_extractor=ai_extractor,
            soup=soup,
            product_url=product_url,
            use_optimized_mode=use_optimized_mode,
            translate_to_english=True,
        )
