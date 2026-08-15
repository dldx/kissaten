"""Monogram Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="monogram",
    display_name="Monogram Coffee",
    roaster_name="Monogram",
    website="https://monogramcoffee.com",
    description="Calgary-based specialty coffee roaster known for innovative, relationship-driven "
    "sourcing and award-winning filter and espresso coffees",
    requires_api_key=True,
    currency="CAD",
    country="Canada",
    status="available",
)
class MonogramScraper(ShopifyJsonScraper):
    """Scraper for Monogram Coffee (monogramcoffee.com) using Shopify products.json.

    The store uses Shopify Markets: the ``/en-us/`` path serves USD-converted
    prices while the market-less base URL serves the store's home currency
    (CAD). We scrape the base (non-market) products.json endpoint so the
    injected JSON prices stay in CAD, matching the roaster's home currency.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Monogram Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Monogram",
            base_url="https://monogramcoffee.com",
            products_json_urls=[
                "https://monogramcoffee.com/collections/all-coffees/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Normalize Monogram Coffee product URLs to the canonical form.

        ShopifyJsonScraper builds URLs by appending the collection segment to
        the products.json base, yielding
        ``.../collections/all-coffees/products/<handle>``. The site's real
        canonical product URLs are ``https://monogramcoffee.com/products/<handle>``
        (no collection segment, no market prefix). Strip the collection segment so
        stored URLs match the live site.
        """
        return url.replace("/collections/all-coffees/products/", "/products/")
