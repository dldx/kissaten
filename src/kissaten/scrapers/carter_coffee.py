"""Carter Coffee scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="carter",
    display_name="Carter Coffee",
    roaster_name="Carter Coffee",
    website="https://cartercoffee.uk",
    description="Edinburgh-based speciality coffee roaster known for experimental "
    "processing: anaerobic-natural single origins, a rotating seasonal house "
    "blend (Bread & Butter), half-caff and sugarcane-decaf options, all "
    "roasted and packed in small batches.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class CarterCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Carter Coffee (cartercoffee.uk) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Carter Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Carter Coffee",
            base_url="https://cartercoffee.uk",
            products_json_urls=[
                "https://cartercoffee.uk/collections/all/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude merch (cap/socks/t-shirt) and the "Carter Daily" subscription
        # pack. Full-handle slugs are used so the substring match can never
        # accidentally drop a coffee.
        self.exclude_slugs = [
            "carter-cap",
            "carter-socks",
            "carter-t-shirt",
            "carter-x-platform-pack",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Canonicalise product URLs to ``<base_url>/products/<handle>``.

        The products.json endpoint lives under ``/collections/all``, so the
        default URL construction yields ``/collections/all/products/...``.
        The live site uses the canonical ``/products/<handle>`` form, so we
        strip the collection segment here. (The store does not use www.)
        """
        url = re.sub(r"/collections/[^/]+(?=/products/)", "", url)
        return url
