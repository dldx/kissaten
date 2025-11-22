"""Le J' Cafe and Roastery scraper implementation."""

import logging

from kissaten.schemas.coffee_bean import CoffeeBean

from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="le-j-roastery",
    display_name="Le J' Cafe and Roastery",
    roaster_name="Le J' Cafe and Roastery",
    website="https://lejcafe.com",
    description="Vietnamese specialty coffee roaster based in Da Lat, Vietnam.",
    requires_api_key=False,
    currency="VND",
    country="Vietnam",
    status="available",
)
class LeJRoasteryScraper(BaseScraper):
    """Scraper for Le J' Cafe and Roastery (lejcafeandroastery.com)."""

    def __init__(self):
        super().__init__(
            roaster_name="Le J' Cafe and Roastery",
            base_url="https://lejcafe.com",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape."""
        return [
            "https://lejcafe.com/collections/all?sort_by=title-ascending&filter.v.availability=1&filter.p.t.category=fb-1-3-1",
        ]

    def _get_excluded_url_patterns(self) -> list[str]:
        return super()._get_excluded_url_patterns() + ["-capsule", "ufo-filter"]

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction.

        Args:
            product_urls: List of URLs for new products

        Returns:
            List of newly scraped CoffeeBean objects
        """
        if not product_urls:
            return []

        # Create a function that returns the product URLs for the AI extraction
        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=False,
            use_optimized_mode=False,
            translate_to_english=True,
        )

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from store page."""
        soup = await self.fetch_page(store_url)
        if not soup:
            return []
        # Use the base class method with Shopify-specific patterns
        extracted_urls = self.extract_product_urls_from_soup(
            soup,
            # Shopify product URL pattern
            url_path_patterns=["/products/"],
            selectors=[
                # Shopify product link selectors
                'a[href*="/products/"]'
            ],
        )
        extracted_urls = [url.split("?")[0] for url in extracted_urls]
        return extracted_urls
