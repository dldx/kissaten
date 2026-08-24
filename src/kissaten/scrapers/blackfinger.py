"""Blackfinger Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="blackfinger",
    display_name="Blackfinger",
    roaster_name="Blackfinger",
    website="https://blackfingercoffee.co.uk",
    description="Queer-owned worker-run cooperative cafe and roastery founded in Camberwell, "
    "London (SE5), opened 13 Jun 2026, roasting small-lot coffees from Colombia, India and Indonesia.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class BlackfingerScraper(ShopifyJsonScraper):
    """Scraper for Blackfinger Coffee (blackfingercoffee.co.uk) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Blackfinger Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Blackfinger",
            base_url="https://blackfingercoffee.co.uk",
            products_json_urls=["https://blackfingercoffee.co.uk/collections/coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The curated "coffee" collection carries the bean detail entirely in the
        # product body_html (Notes/Origin/Region/Altitude/Producer/Process), so the
        # JSON-only optimized path is sufficient and cheapest for this tiny catalog.
        # Pin the currency to GBP (the products.json payload carries no currency field)
        # and mark it as detected so the collection-page detection path is skipped.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Exclude genuine services (monthly subscription) plus common non-coffee
        # categories, defensively. The curated coffee collection currently holds
        # only the three beans, but keep the slug guard in case it changes.
        self.exclude_slugs = [
            "subscription",
            "coffee-club",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "apparel",
            "mug",
            "tumbler",
            "hoodie",
            "tshirt",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Blackfinger product URLs.

        The site's canonical product pages are ``/products/<handle>`` (no collection
        segment), so strip the ``/collections/coffee`` prefix that the base class
        derives from the products.json URL base.
        """
        return url.replace("/collections/coffee/products/", "/products/")
