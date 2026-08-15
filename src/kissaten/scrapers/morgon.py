"""Morgon Coffee Roasters scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="morgon",
    display_name="Morgon",
    roaster_name="Morgon",
    website="https://www.morgoncoffeeroasters.com/",
    description="Swedish specialty coffee roaster based in Gothenburg, crafting "
    "carefully sourced single origin coffees roasted for filter and espresso.",
    requires_api_key=True,
    currency="SEK",
    country="Sweden",
    status="available",
)
class MorgonScraper(ShopifyJsonScraper):
    """Scraper for Morgon Coffee Roasters (morgoncoffeeroasters.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Morgon Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Morgon",
            base_url="https://www.morgoncoffeeroasters.com",
            products_json_urls=[
                "https://www.morgoncoffeeroasters.com/collections/coffee/products.json",
                "https://www.morgoncoffeeroasters.com/collections/espresso/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=1.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude non-coffee products (gift cards, subscriptions, merch, gear)
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "giftcard",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "merch",
            "beanie",
            "hat",
            "poster",
            "filters",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

        # Remove the Accept-Language header so Shopify serves the base SEK
        # market instead of a geo-localized presentment currency (e.g. GBP).
        # Morgon's products.json prices are SEK; any Accept-Language (even
        # sv-SE) makes Shopify present a converted currency to this scraper.
        self.headers.pop("Accept-Language", None)
        self.client._base_headers.pop("Accept-Language", None)
        session_headers = getattr(self.client._session, "headers", None)
        if session_headers:
            session_headers.pop("Accept-Language", None)

    def _extract_currency_from_html(self, soup) -> str:
        """Pin the store currency to SEK.

        Morgon is a Swedish roaster priced in SEK (the products.json prices
        are SEK). The site serves a geo-localized presentment currency (e.g.
        GBP) in its ``Shopify.currency`` script and ``og:price:currency`` meta,
        which would otherwise override the correct base currency during
        extraction. Force SEK so the AI prices the beans correctly.
        """
        return "SEK"

    def postprocess_extracted_bean(self, bean):
        """Force the bean currency to SEK (store base currency)."""
        bean = super().postprocess_extracted_bean(bean)
        bean.currency = "SEK"
        return bean

    def preprocess_product_url(self, url: str) -> str:
        """Strip the collection segment from product URLs.

        Morgon's canonical product pages are just ``/products/<handle>`` (no
        collection prefix), so remove the ``/collections/<name>/`` added by
        the Shopify base from the collection products.json URLs.
        """
        return re.sub(r"/collections/[^/]+/products/", "/products/", url)
