"""Groupwork Coffee Roasters scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="groupwork",
    display_name="Groupwork",
    roaster_name="Groupwork",
    website="https://groupworkcoffee.com",
    description="London-based coffee roaster built on a 'better shared' collaboration "
    "model, where each coffee (PROJECT, FIELD TRIP, PARTNERSHIP, COMMUNITY, BALANCE) "
    "is a shared creation with partner producers and growers.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class GroupworkScraper(ShopifyJsonScraper):
    """Scraper for Groupwork Coffee Roasters (groupworkcoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Groupwork Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Groupwork",
            base_url="https://groupworkcoffee.com",
            products_json_urls=["https://groupworkcoffee.com/collections/coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=1.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Exclude non-coffee products (subscriptions, gift cards, merch, gear)
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

        # Remove the Accept-Language header so Shopify serves the base GBP
        # market instead of a geo-localized presentment currency. Groupwork is
        # a London roaster priced in GBP; any Accept-Language can make Shopify
        # present a converted currency to this scraper.
        self.headers.pop("Accept-Language", None)
        self.client._base_headers.pop("Accept-Language", None)
        session_headers = getattr(self.client._session, "headers", None)
        if session_headers:
            session_headers.pop("Accept-Language", None)

    def _extract_currency_from_html(self, soup) -> str:
        """Pin the store currency to GBP.

        Groupwork is a London roaster priced in GBP (the products.json prices
        are GBP). The site may serve a geo-localized presentment currency in
        its ``Shopify.currency`` script for datacenter IPs, so force GBP to
        keep the AI pricing beans correctly.
        """
        return "GBP"

    def postprocess_extracted_bean(self, bean):
        """Force the bean currency to GBP (store base currency)."""
        bean = super().postprocess_extracted_bean(bean)
        if bean is not None:
            bean.currency = "GBP"
        return bean

    def preprocess_product_url(self, url: str) -> str:
        """Strip the collection segment from product URLs.

        Groupwork's canonical product pages are just ``/products/<handle>``
        (no collection prefix), so remove the ``/collections/<name>/`` added
        by the Shopify base from the collection products.json URL.
        """
        return re.sub(r"/collections/[^/]+/products/", "/products/", url)
