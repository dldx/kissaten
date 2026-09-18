"""Muttley & Jack's Coffee Roasters scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="muttley-jacks",
    display_name="Muttley & Jack's Coffee Roasters",
    roaster_name="Muttley & Jack's Coffee Roasters",
    website="https://muttleyandjacks.se",
    description="Swedish specialty coffee roaster on Värmdö near Stockholm roasting "
    "single origins and classic Swedish blends, home of the James Hoffmann "
    "Fermentation Project box with Lucia Solis.",
    requires_api_key=True,
    currency="SEK",
    country="Sweden",
    status="experimental",
)
class MuttleyJacksScraper(ShopifyJsonScraper):
    """Scraper for Muttley & Jack's (muttleyandjacks.se) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Muttley & Jack's scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Muttley & Jack's Coffee Roasters",
            base_url="https://muttleyandjacks.se",
            products_json_urls=["https://muttleyandjacks.se/collections/all/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=1.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # collections/all mixes coffee with gift memberships, coffee-experience
        # subscription boxes, gift cards, shipping and food/equipment items.
        # Tasting kits (smaklåda, seasonal tasting box) are deliberately kept —
        # they are flagged for review downstream.
        self.exclude_slugs = [
            "gavomedlemskap",
            "gift-card",
            "500-kr",
            "sverige-frakt",
            "adventure",
            "sharing-box",
            "piccolo-box",
            "passport",
            "voyage",
            "sallader",
            "hario-v60",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Strip the collection segment to match Muttley & Jack's canonical product URLs.

        ShopifyJsonScraper builds product URLs as
        ``<products.json base>/products/<handle>``, which yields a
        ``/collections/all/products/<handle>`` form. Muttley & Jack's canonical
        product pages are served at ``/products/<handle>``.
        """
        return re.sub(r"/collections/[^/]+/products/", "/products/", url)
