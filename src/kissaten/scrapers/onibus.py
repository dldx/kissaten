"""Onibus Coffee scraper implementation with Shopify JSON extraction.

Onibus Coffee is a specialty coffee roaster based in Tokyo, Japan. The store
is hosted on Shopify and serves a localized Japanese view (the ``/en/`` path
exists but still returns Japanese content), so extracted beans are always
translated to English.
"""

import logging
from typing import Any

from ..schemas import CoffeeBean
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="onibus",
    display_name="Onibus",
    roaster_name="Onibus",
    website="https://onibuscoffee.com/en/",
    description="Specialty coffee roaster based in Tokyo, Japan, sourcing single "
    "origin coffees directly from farms and featuring original blends.",
    requires_api_key=True,
    currency="JPY",
    country="Japan",
    status="available",
)
class OnibusScraper(ShopifyJsonScraper):
    """Scraper for Onibus Coffee (onibuscoffee.com) using Shopify products.json.

    The Shopify JSON for each coffee product already carries the full bean
    detail (origin, farm, producer, variety, process, elevation, tasting notes
    and description), so product pages are not fetched for AI extraction.
    Because the content is authored in Japanese, extracted beans are always
    translated to English.
    """

    def preprocess_product_url(self, url: str) -> str:
        """Normalize product URLs to the canonical ``/en/products/<handle>`` form.

        ShopifyJsonScraper builds product URLs from the products.json base,
        which yields ``/en/collections/coffee/products/<handle>``. Onibus's
        canonical product pages are just ``/en/products/<handle>``, so the
        collection segment is stripped.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1]
            return f"{self.base_url}/products/{handle}"
        return url

    async def _extract_bean_with_ai(
        self,
        ai_extractor: Any,
        soup: Any,
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
        """Initialize the Onibus Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Onibus",
            base_url="https://onibuscoffee.com/en",
            products_json_urls=[
                "https://onibuscoffee.com/en/collections/coffee/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

        # Exclude non-bean products that appear in the coffee collection
        # (subscriptions, cold brew packs, tasting sets, drip bags, gift items).
        self.exclude_slugs = [
            "subscription",
            "monthlybox",
            "coldbrew",
            "tastingset",
            "dripbag",
            "gift",
        ]
