"""Three Marks Coffee scraper.

Spanish specialty coffee roaster offering single origin coffees
from various regions including Brazil, Mexico, Ethiopia, Rwanda, and more.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="three-marks-coffee",
    display_name="Three Marks Coffee",
    roaster_name="Three Marks Coffee",
    website="https://threemarkscoffee.com",
    description="Spanish specialty coffee roaster offering single origin and "
    "seasonal coffee marks from around the world",
    requires_api_key=True,  # Using AI extraction for best results
    currency="EUR",
    country="Spain",
    status="available",
)
class ThreeMarksCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Three Marks Coffee using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize the scraper.

        Args:
            api_key: Optional API key for AI-powered extraction
        """
        super().__init__(
            roaster_name="Three Marks Coffee",
            base_url="https://www.threemarkscoffee.com",
            products_json_urls=[
                "https://www.threemarkscoffee.com/products.json",
            ],
            rate_limit_delay=1.5,
            max_retries=3,
            timeout=30.0,
        )

        # Exclude non-coffee products
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "curso-completo-barista-3",
            "-coffee-bags",
            "capsules",
            "bundle",
            "equipment",
            "merchandise",
            "color-tray",
            "185-",
            "3x",
            "2x",
            "1x",
            "dripcoffee",
            "-box",
            "sibarist",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
