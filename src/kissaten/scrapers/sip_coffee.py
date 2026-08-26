"""SIP Collective scraper implementation with Shopify JSON extraction.

SIP Collective is a UK specialty coffee roaster (sipcoffee.co) that imports
rare, traceable microlots from producers worldwide and roasts to order in
Glasgow. The Shopify ``collections/coffee/products.json`` feed carries the
full bean detail (producer/cooperative narrative, processing, tasting notes)
in each product's ``body_html``, so extraction is done JSON-only with
optimized mode — no product-page scraping needed.

Currency is pinned to GBP and the country to the United Kingdom. Only
whole-bean coffee is kept; brewing equipment that shares the coffee
collection is excluded by slug.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="sip-coffee",
    display_name="SIP Collective",
    roaster_name="SIP Collective",
    website="https://sipcoffee.co",
    description="Glasgow-based specialty coffee roaster sourcing rare, "
    "direct microlots from producers worldwide and roasting to order. "
    "Co-founded by UK Barista Champion Anthos Thoma.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class SipCoffeeScraper(ShopifyJsonScraper):
    """Scraper for SIP Collective (sipcoffee.co) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize SIP Collective scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="SIP Collective",
            base_url="https://sipcoffee.co",
            products_json_urls=[
                "https://sipcoffee.co/collections/coffee/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Pin currency: the store serves the UK market (GBP) and must never
        # let IP/Accept-Language geo-detection stamp a converted currency.
        self.store_currency = "GBP"
        self._currency_detected = True

        # The curated coffee collection mixes in a couple of brewing-accessory
        # items; exclude those plus the usual non-bean categories. Samplers /
        # tasting kits are deliberately NOT excluded — they are flagged by
        # _apply_product_flags and land in the admin review queue.
        self.exclude_slugs = [
            "clever-coffee-dripper",
            "coffee-scale",
            "timemore",
            "aeropress",
            "subscription",
            "gift-card",
            "equipment",
            "brewing",
            "merchandise",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize SIP Collective product URLs.

        The site's canonical product pages are the no-collection form
        ``/products/<handle>``. The base class builds
        ``/collections/coffee/products/<handle>`` from the collection
        products.json URL, so strip the collection segment to keep URLs
        aligned with the real site.
        """
        return url.replace("/collections/coffee/products/", "/products/")
