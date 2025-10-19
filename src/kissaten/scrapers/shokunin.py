"""Shokunin Coffee Roasters scraper implementation."""

import logging

from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="shokunin",
    display_name="Shokunin Coffee Roasters",
    roaster_name="Shokunin Coffee Roasters",
    website="https://shokunin.coffee",
    description="Roaster based in Rotterdam, focused on high-quality specialty coffee.",
    requires_api_key=False,
    currency="EUR",
    country="Netherlands",
    status="available",
)
class ShokuninCoffeeRoastersScraper(BaseScraper):
    """Scraper for Shokunin Coffee Roasters (shokunin.coffee)."""

    def __init__(self):
        super().__init__(
            roaster_name="Shokunin Coffee Roasters",
            base_url="https://shokunin.coffee",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape."""
        return ["https://shokunin.coffee/shop/"]

    def _get_excluded_url_patterns(self) -> list[str]:
        return super()._get_excluded_url_patterns() + [
            "-mug",
            "-pin",
            "green-coffee",
            "cups",
            "surprise",
        ]

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from store page."""
        soup = await self.fetch_page(store_url)
        if not soup:
            return []
        # Use the base class method with Shopify-specific patterns
        return self.extract_product_urls_from_soup(
            soup,
            # Shopify product URL pattern
            url_path_patterns=["/product/"],
            selectors=[
                # Shopify product link selectors
                'a.pushed[href*="/product/"]'
            ],
        )
