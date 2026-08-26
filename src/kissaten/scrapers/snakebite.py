"""Snakebite Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="snakebite",
    display_name="Snakebite Coffee",
    roaster_name="Snakebite Coffee",
    website="https://snakebitecoffee.co",
    description="London-based specialty coffee roaster (Snakebite Coffee Co), roasting "
    "single-origin and house-blend whole beans for espresso and filter brewing.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class SnakebiteCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Snakebite Coffee (snakebitecoffee.co) using Shopify products.json.

    The site is a Shopify storefront. We scrape the curated ``all-coffee``
    collection, which holds every whole-bean coffee plus a survival sampler
    pack. Non-coffee items (gift card) are dropped by the base coffee-name
    filtering; the sampler is kept and flagged ``is_tasting_kit`` /
    ``requires_review`` by the base ``_apply_product_flags`` pipeline into the
    admin review queue rather than excluded. Product URLs are canonicalized to
    the no-collection ``/products/<handle>`` form the site actually serves.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Snakebite Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Snakebite Coffee",
            base_url="https://snakebitecoffee.co",
            products_json_urls=["https://snakebitecoffee.co/collections/all-coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The all-coffee collection carries only whole-bean coffee plus a
        # sampler (kept & flagged for review) and a gift card (dropped by the
        # base coffee-name filter). No slug exclusions are needed, and none are
        # applied so samplers/tasting kits are never silently dropped.
        self.exclude_slugs = []

        # UK roaster — pin the home-market currency (GBP) so Shopify Markets
        # geolocation cannot stamp converted prices onto the beans.
        self.store_currency = "GBP"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Canonicalize Snakebite product URLs to the no-collection form.

        The ``all-coffee`` products.json base yields
        ``/collections/all-coffee/products/<handle>``, but the site's real
        product pages are just ``/products/<handle>``. Strip the collection
        segment so URLs match the canonical form (and historical data).
        """
        url = url.replace("/collections/all-coffee/products/", "/products/")
        return url
