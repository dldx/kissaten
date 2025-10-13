"""Vibe With Coffee Roastery scraper implementation."""

import logging

from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="vibe-with",
    display_name="Vibe With Coffee Roastery",
    roaster_name="Vibe With Coffee Roastery",
    website="https://vibewithcoffee.com",
    description="Nottingham-based specialty coffee roastery and café, focusing on precision and scientific principles.",
    requires_api_key=False,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class VibeWithCoffeeRoasteryScraper(BaseScraper):
    """Scraper for Vibe With Coffee Roastery (vibewithcoffee.com)."""

    def __init__(self):
        super().__init__(
            roaster_name="Vibe With Coffee Roastery",
            base_url="https://vibewithcoffee.com",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape."""
        return [
            "https://www.vibewithcoffee.com/coffee",
        ]

    def _get_excluded_url_patterns(self) -> list[str]:
        return super()._get_excluded_url_patterns() + ["-capsule"]

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from store page."""
        soup = await self.fetch_page(store_url)
        if not soup:
            return []
        # Use the base class method with Shopify-specific patterns
        return self.extract_product_urls_from_soup(
            soup,
            # Shopify product URL pattern
            url_path_patterns=["/product-page/"],
            selectors=[
                # Shopify product link selectors
                'a[href*="/product-page/"][data-hook="product-item-container"]'
            ],
        )
