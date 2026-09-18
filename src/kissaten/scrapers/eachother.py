"""Eachother scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="eachother",
    display_name="Eachother",
    roaster_name="Eachother",
    website="https://eachother.rocks",
    description="Small specialty coffee roaster focused on carefully sourced, "
    "individually profiled single-origin coffees",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class EachotherScraper(ShopifyJsonScraper):
    """Scraper for Eachother (eachother.rocks) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Eachother scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Eachother",
            base_url="https://eachother.rocks",
            products_json_urls=[
                "https://eachother.rocks/collections/coffees/products.json",
                # The Fermentation Project kit lives in its own collection and
                # is not part of the coffees collection.
                "https://eachother.rocks/collections/the-fermentation-project/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # No exclusions needed: the coffees collections only hold beans plus
        # the Fermentation Project tasting kit (kept — flagged downstream).

        # Pin the home-market currency: Shopify Markets can geo-convert prices
        # for datacenter IPs; cart.js from the home market reports USD.
        self.store_currency = "USD"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize product URLs to the canonical /products/<handle> form.

        The site's product sitemap uses the no-collection URL form; stripping
        the collection segment also de-duplicates the kit listed in two
        collections.
        """
        return re.sub(r"/collections/[^/]+/products/", "/products/", url)
