"""Space Coffee Roastery scraper implementation."""

import logging

from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="space-roastery",
    display_name="Space Coffee Roastery",
    roaster_name="Space Coffee Roastery",
    website="https://spaceroastery.com",
    description="Indonesian roaster based in Yogyakarta, Java.",
    requires_api_key=False,
    currency="IDR",
    country="Indonesia",
    status="available",
)
class SpaceCoffeeRoasteryScraper(BaseScraper):
    """Scraper for Space Coffee Roastery (spaceroastery.com)."""

    def __init__(self):
        super().__init__(
            roaster_name="Space Coffee Roastery",
            base_url="https://spaceroastery.com",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape."""
        return [
            "https://spaceroastery.com/products/shop-coffee/single-origin001",
            "https://spaceroastery.com/products/shop-coffee/blend001",
            "https://spaceroastery.com/products/shop-coffee/limited-release",
        ]

    def _get_excluded_url_patterns(self) -> list[str]:
        return super()._get_excluded_url_patterns() + ["-capsule", "any-coffee-you-like"]

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from store page."""
        soup = await self.fetch_page(store_url)
        if not soup:
            return []
        # Use the base class method with Shopify-specific patterns
        return self.extract_product_urls_from_soup(
            soup,
            # Shopify product URL pattern
            url_path_patterns=["/products/"],
            selectors=[
                # Shopify product link selectors
                'a.anchor-default[href*="/products/"]'
            ],
        )
