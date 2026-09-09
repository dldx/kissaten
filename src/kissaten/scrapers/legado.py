"""Legado scraper implementation with Shopify JSON extraction.

Legado (legadocoffee.com) is a Johannesburg, South Africa-based specialty
coffee roaster. The store is Shopify-hosted and priced in ZAR.

The curated ``coffee-beans`` collection ("Freshly Roasted Coffee") holds the
full retail bean line-up (single origins and blends, ``product_type ==
"Retail Coffee"``); the broader ``all`` collection only adds event-catering
packages. The ``body_html`` already carries variety, altitude, processing
method and tasting notes, so the scraper uses JSON-only extraction
(``scrape_product_pages=False``).

The store serves unconverted ZAR prices from this machine (SAST timestamps,
ZAR-magnitude prices), but as a Shopify Markets store it could geo-convert
prices for a datacenter IP, so we pin the store currency to ZAR in ``__init__``
and remove the ``Accept-Language`` header.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="legado",
    display_name="Legado",
    roaster_name="Legado",
    website="https://legadocoffee.com",
    description="Johannesburg specialty coffee roaster offering single origins "
    "and blends, roasted in South Africa and priced in ZAR",
    requires_api_key=True,
    currency="ZAR",
    country="South Africa",
    status="available",
)
class LegadoScraper(ShopifyJsonScraper):
    """Scraper for Legado (legadocoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Legado scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Legado",
            base_url="https://legadocoffee.com",
            products_json_urls=[
                "https://legadocoffee.com/collections/coffee-beans/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Pin the store currency to the home-market ZAR. The site is a
        # Shopify Markets store; a datacenter IP may receive geo-converted
        # prices, so the geo-detected value must never override ZAR.
        self.store_currency = "ZAR"
        self._currency_detected = True

        # Exclude genuine non-coffee products only. The curated coffee-beans
        # collection is already coffee-only (Retail Coffee product_type); the
        # net below guards against the event/catering packages and merch that
        # live in the broader `all` collection leaking in later. Any tasting
        # kit that slips through is flagged for review by the base
        # ``_apply_product_flags`` pipeline instead of being silently dropped.
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
            "apparel",
            "tee",
            "mug",
            "event",
            "catered",
            "venue",
        ]

        # Remove the Accept-Language header so Shopify serves the base ZAR
        # market instead of a geo-localized presentment currency (any
        # Accept-Language, even en-US, can trigger conversion).
        self.headers.pop("Accept-Language", None)
        self.client._base_headers.pop("Accept-Language", None)
        session_headers = getattr(self.client._session, "headers", None)
        if session_headers:
            session_headers.pop("Accept-Language", None)

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def _extract_currency_from_html(self, soup) -> str:
        """Pin the store currency to ZAR.

        Legado is a South African roaster priced in ZAR (the products.json
        prices are ZAR). Shopify Markets could serve a geo-localized
        presentment currency based on the caller's IP, which would otherwise
        override the correct base currency during extraction. Force ZAR so
        the AI prices the beans correctly.
        """
        return "ZAR"

    def postprocess_extracted_bean(self, bean):
        """Force the bean currency to ZAR (store base currency)."""
        bean = super().postprocess_extracted_bean(bean)
        bean.currency = "ZAR"
        return bean
