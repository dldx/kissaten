"""Passenger Coffee scraper implementation using the Shopify products.json API.

Passenger Coffee (passengercoffee.com) is a specialty coffee roaster based in
Lancaster, Pennsylvania, USA. The storefront is Shopify-hosted and serves a
working products.json endpoint, but the rendered product pages (which live on
the canonical drinkpassenger.com domain) are behind a bot-protection layer that
returns HTTP 401 even to headless Playwright browsers. We therefore scrape in
JSON-only mode: discovery, stock status, pricing, and the rich product/bean
metadata all come from the products.json payload, which carries the full
``body_html`` description (origin, process, variety, tasting notes, etc.).
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="passenger",
    display_name="Passenger",
    roaster_name="Passenger",
    website="https://passengercoffee.com",
    description="Lancaster-based specialty coffee roaster known for "
    "transparently sourced single-origin and reserve lot coffees",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="available",
)
class PassengerCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Passenger Coffee (passengercoffee.com / drinkpassenger.com).

    Uses the coffee-specific ``/collections/coffee/products.json`` endpoint so
    the catalog is naturally limited to coffee beans. Product pages are
    bot-protected (HTTP 401) on both domains, so ``scrape_product_pages`` is
    disabled and extraction runs purely on the injected Shopify JSON context.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize the Passenger Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try the environment.
        """
        super().__init__(
            roaster_name="Passenger",
            base_url="https://passengercoffee.com",
            products_json_urls=[
                "https://passengercoffee.com/collections/coffee/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=1.5,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The coffee collection is already curated to beans; keep the standard
        # exclude list only as a safety net for anything that sneaks in
        # (subscriptions, gift cards, equipment, merchandise).
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "merch",
            "bundle",
            "apparel",
            "mug",
            "tumbler",
            "hoodie",
            "tshirt",
            "capsules",
            "pods",
            "cold-brew-cans",
            "easy-pour",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize product URLs to the site's canonical form.

        The site's real product pages are served from the canonical
        ``https://drinkpassenger.com/products/<handle>`` path (per the store's
        sitemap and HTTP redirects), not the collection-prefixed passengercoffee.com
        form that the Shopify base class derives from the products.json URL base.
        We strip the collection segment and rewrite onto drinkpassenger.com so the
        stored bean URLs match the URLs the site actually serves.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1]
            return f"https://drinkpassenger.com/products/{handle}"
        return url
