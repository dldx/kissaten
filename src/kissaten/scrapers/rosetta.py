"""Rosetta Roastery scraper implementation with Shopify JSON extraction.

Rosetta Roastery is a Cape Town, South Africa-based specialty roaster on a
Shopify storefront priced in ZAR. The curated ``coffee`` collection holds the
full bean catalogue (single origins, blends, a decaf, drip sachet boxes and a
multi-bag signature selection set), so it is used instead of
``collections/all`` (which also carries subscriptions, equipment and merch).

The products.json ``body_html`` already carries the bean detail (tasting
notes, producer, region, altitude, variety, processing, harvest) plus price
variants, so the scraper uses JSON-only extraction
(``scrape_product_pages=False``).

The store serves ZAR (rate 1.0) even from a datacenter IP, but as a defensive
measure against Shopify Markets currency geolocation the store currency is
pinned to ZAR in ``__init__`` and the ``Accept-Language`` header is removed.
Product URLs are canonicalised to the no-collection ``/products/<handle>``
form the live site serves.
"""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="rosetta",
    display_name="Rosetta Roastery",
    roaster_name="Rosetta Roastery",
    website="https://www.rosettaroastery.com",
    description="Cape Town, South Africa specialty roaster pursuing 'coffee perfection' "
    "with rotating single origins, blends and a decaf on a Shopify storefront priced in ZAR",
    requires_api_key=True,
    currency="ZAR",
    country="South Africa",
    status="available",
)
class RosettaScraper(ShopifyJsonScraper):
    """Scraper for Rosetta Roastery (rosettaroastery.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Rosetta Roastery scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Rosetta Roastery",
            base_url="https://www.rosettaroastery.com",
            products_json_urls=[
                "https://www.rosettaroastery.com/collections/coffee/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Pin the store currency to the home-market ZAR. The site is Shopify
        # Markets-capable; a datacenter IP must never be able to stamp
        # geo-converted prices onto beans.
        self.store_currency = "ZAR"
        self._currency_detected = True

        # Exclude genuine non-coffee products only (coffee capsules/pods are
        # equipment-adjacent, not beans). Drip sachet boxes and the multi-bag
        # Signature Selection set are kept: any product the AI extractor
        # recognises as a tasting kit is flagged for review by the base
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
            "capsules",
            "pods",
        ]

        # Remove the Accept-Language header so Shopify serves the base ZAR
        # market instead of a geo-localized presentment currency (any
        # Accept-Language, even the home one, can trigger conversion).
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

        Rosetta Roastery is a South African roaster priced in ZAR (the
        products.json prices are ZAR). Force ZAR so a geo-localized Shopify
        Markets presentment currency can never override the base currency
        during extraction.
        """
        return "ZAR"

    def postprocess_extracted_bean(self, bean):
        """Force the bean currency to ZAR (store base currency)."""
        bean = super().postprocess_extracted_bean(bean)
        bean.currency = "ZAR"
        return bean

    def preprocess_product_url(self, url: str) -> str:
        """Strip the collection segment from product URLs.

        Rosetta's canonical product pages are just ``/products/<handle>``
        (no collection prefix), so remove the ``/collections/<name>/`` added
        by the Shopify base from the collection products.json URL.
        """
        return re.sub(r"/collections/[^/]+/products/", "/products/", url)
