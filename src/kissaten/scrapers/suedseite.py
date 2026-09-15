"""Suedseite Kaffeerösterei scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="suedseite",
    display_name="Suedseite",
    roaster_name="Suedseite",
    website="https://suedseite.coffee",
    description="Leipzig-based German specialty coffee roaster offering single "
    "origins and blends, including the James Hoffmann / Lucia Solis "
    "Fermentation Project.",
    requires_api_key=True,
    currency="EUR",
    country="Germany",
    status="experimental",
)
class SuedseiteScraper(ShopifyJsonScraper):
    """Scraper for Suedseite (suedseite.coffee) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Suedseite scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Suedseite",
            base_url="https://suedseite.coffee",
            products_json_urls=["https://suedseite.coffee/collections/alle-bohnen/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The curated alle-bohnen collection holds only beans (including the
        # Fermentation Project coffee, which is kept); exclude the "Best of
        # Suedseite" coffee subscription (Abo).
        self.exclude_slugs = [
            "abo",
            "subscription",
            "gift-card",
            "gift",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
