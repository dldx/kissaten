"""Yellow Jacket Coffee scraper implementation with Shopify JSON extraction.

Yellow Jacket Coffee (yellowjacketcoffee.co.za) is a South African specialty
coffee roaster. The store is Shopify-hosted and priced in ZAR.

There is no single curated coffee collection that covers the whole bean
line-up (``new-releases`` holds the single origins but misses the house blends
"Komodo" and "Circus Bear"), so we use ``collections/all`` with an
``exclude_slugs`` net for the genuine equipment items (scales, V60s, cloths,
filter holders, water sachets). The "5 Pack - Filter Drip Pack" is kept: it is
coffee, and if the AI extractor recognises it as a tasting kit it is flagged
for review by the base ``_apply_product_flags`` pipeline.

The ``body_html`` already carries flavour notes and extensive farm/processing
detail, so the scraper uses JSON-only extraction (``scrape_product_pages=False``).

Product URLs are canonicalised to the no-collection ``/products/<handle>``
form: ``/collections/<name>/products/<handle>`` URLs 301-redirect there on the
live site.

The store serves unconverted ZAR prices from this machine (SAST timestamps,
ZAR-magnitude prices), but as a Shopify Markets store it could geo-convert
prices for a datacenter IP, so we pin the store currency to ZAR in ``__init__``
and remove the ``Accept-Language`` header.
"""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="yellow-jacket",
    display_name="Yellow Jacket Coffee",
    roaster_name="Yellow Jacket Coffee",
    website="https://yellowjacketcoffee.co.za",
    description="South African specialty coffee roaster offering single origins "
    "and house blends from African and Latin American producers, priced in ZAR",
    requires_api_key=True,
    currency="ZAR",
    country="South Africa",
    status="available",
)
class YellowJacketScraper(ShopifyJsonScraper):
    """Scraper for Yellow Jacket Coffee (yellowjacketcoffee.co.za) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Yellow Jacket Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Yellow Jacket Coffee",
            base_url="https://yellowjacketcoffee.co.za",
            products_json_urls=[
                "https://yellowjacketcoffee.co.za/collections/all/products.json",
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

        # Exclude genuine non-coffee products only: the equipment items that
        # share the `all` collection with the beans (no curated coffee-only
        # collection exists that covers the blends). The Filter Drip Pack is
        # kept — it is coffee, and any recognised tasting kit is flagged for
        # review by the base ``_apply_product_flags`` pipeline.
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
            # Yellow Jacket equipment handles
            "barista",  # Barista Cloths
            "espresso-scale",  # Compact Espresso Scale
            "filter-holder",  # Metal/Wooden Coffee Paper Filter Holder
            "one-cup-v60",  # One Cup V60 with Filters
            "v60-2-cup",  # V60 2 Cup
            "third-wave-water",  # Third Wave Water Mineral Sachets
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

        Yellow Jacket Coffee is a South African roaster priced in ZAR (the
        products.json prices are ZAR). Shopify Markets could serve a
        geo-localized presentment currency based on the caller's IP, which
        would otherwise override the correct base currency during extraction.
        Force ZAR so the AI prices the beans correctly.
        """
        return "ZAR"

    def postprocess_extracted_bean(self, bean):
        """Force the bean currency to ZAR (store base currency)."""
        bean = super().postprocess_extracted_bean(bean)
        bean.currency = "ZAR"
        return bean

    def preprocess_product_url(self, url: str) -> str:
        """Strip the collection segment from product URLs.

        Yellow Jacket Coffee's canonical product pages are just
        ``/products/<handle>`` (no collection prefix): collection-prefixed
        URLs 301-redirect there, so remove the ``/collections/<name>/``
        segment added by the Shopify base from the collection products.json
        URLs.
        """
        return re.sub(r"/collections/[^/]+/products/", "/products/", url)
