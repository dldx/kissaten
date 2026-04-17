"""Black & White Coffee Roasters scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="black-white-coffee-roasters",
    display_name="Black & White Coffee Roasters",
    roaster_name="Black & White Coffee Roasters",
    website="https://www.blackwhiteroasters.com",
    description="Coffee roaster based in Raleigh, North Carolina committed to connecting people to the most interesting and approachable coffees that they can find.",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="available",
)
class BlackWhiteCoffeeRoastersScraper(ShopifyJsonScraper):
    """Scraper using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Black & White Coffee Roasters",
            base_url="https://www.blackwhiteroasters.com",
            products_json_urls=[
                "https://www.blackwhiteroasters.com/collections/all-coffee/products.json",
            ],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )
        # Exclude subscription products or other non-coffee items
        self.exclude_slugs = ["subscription", "drip-bag", "bundle", "pods", "cascara", "gift-card"]
