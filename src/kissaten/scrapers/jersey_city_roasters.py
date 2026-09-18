"""Jersey City Roasters scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="jersey-city-roasters",
    display_name="Jersey City Roasters",
    roaster_name="Jersey City Roasters",
    website="https://jerseycityroasters.com",
    description="Jersey City-based specialty coffee roaster offering a rotating "
    "line-up of single origins and co-fermented microlots",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class JerseyCityRoastersScraper(ShopifyJsonScraper):
    """Scraper for Jersey City Roasters (jerseycityroasters.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Jersey City Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Jersey City Roasters",
            base_url="https://jerseycityroasters.com",
            # The storefront has a single (frontpage) collection that holds the
            # whole coffee catalogue.
            products_json_urls=["https://jerseycityroasters.com/collections/frontpage/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # No exclusions needed: the frontpage collection only holds beans plus
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

        The site's product sitemap uses the no-collection URL form.
        """
        return re.sub(r"/collections/[^/]+/products/", "/products/", url)
