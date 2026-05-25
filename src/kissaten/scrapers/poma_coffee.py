"""Rish Coffee Roasters scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="poma-coffee",
    display_name="Poma Coffee",
    roaster_name="Poma Coffee",
    website="https://www.pomacoffee.com",
    description="A coffee research and roasting company based in Copenhagen",
    requires_api_key=True,
    currency="DKK",
    country="Denmark",
    status="available",
)
class PomaCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Poma Coffee (pomacoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Poma Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Poma Coffee",
            base_url="https://www.pomacoffee.com",
            products_json_urls=[
                "https://www.pomacoffee.com/collections/all/products.json",
            ],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )
        # Exclude subscription products or other non-coffee items
        self.exclude_slugs = [
            "subscription",
            "drip-",
            "bundle",
            "single-dose-coffee-vial",
            "mineral",
            "dripper",
            "tritan",
            "-pamphlet",
        ]
