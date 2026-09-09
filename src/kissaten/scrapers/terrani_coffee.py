"""Terrani Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="terrani-coffee",
    display_name="Terrani Coffee",
    roaster_name="Terrani Coffee",
    website="https://www.terranicoffee.store",
    description="Nairobi-based Kenyan specialty coffee roaster sourcing high-quality Arabica "
    "directly from local farmers; small-batch roasts sold as washed, anaerobic natural and "
    "dark-roast blends across Kenya",
    requires_api_key=True,
    currency="KES",
    country="Kenya",
    status="available",
)
class TerraniCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Terrani Coffee (www.terranicoffee.store) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Terrani Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Terrani Coffee",
            base_url="https://www.terranicoffee.store",
            products_json_urls=["https://www.terranicoffee.store/collections/freshest-batch-of-coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Pin the home-market currency: Shopify.currency reports KES (rate 1.0),
        # so guard against any geolocation-based conversion by downstream fetches.
        self.store_currency = "KES"
        self._currency_detected = True

        # The curated collection already contains only coffee (beans, samplers,
        # drip boxes) — tasting kits/samplers must flow through flagged for
        # review, so only exclude genuine non-coffee products.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Terrani Coffee product URLs.

        The site's own nav links to the no-collection form (/products/<handle>),
        so strip the collection segment the base class adds from the
        products.json URL base.
        """
        return url.replace("/collections/freshest-batch-of-coffee/products/", "/products/")
