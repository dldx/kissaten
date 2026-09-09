"""Sorcery Coffee Roasters scraper implementation with Shopify JSON extraction.

Sorcery Coffee Roasters (sorcerycoffee.co.za) is a light-roast specialty
roaster with cafés in Hillcrest and Wapadrand, Pretoria, South Africa. The
store is Shopify-hosted and priced in ZAR.

The site has no dedicated "coffee" collection: ``collections/all`` carries the
full catalogue (8 products: 7 bean coffees plus compostable coffee pods — the
beans are split across the storefront's "Approachable" and "Progressive"
ranges, whose union is exactly ``all``). We use ``all`` and drop the pods via
``exclude_slugs``; no tasting kits/samplers are excluded — any that appear are
flagged by the base ``_apply_product_flags`` pipeline instead.

The products.json ``body_html`` already carries the bean detail (region, farm,
producer, altitude, variety, drying/processing, green score, tasting notes)
plus size variants, so the scraper uses JSON-only extraction
(``scrape_product_pages=False``).

The store runs Shopify Markets with currency geolocation, so we pin the store
currency to ZAR (the site's home-market currency) in ``__init__``, from
``_extract_currency_from_html`` and again in ``postprocess_extracted_bean`` so
a datacenter IP can never stamp geo-converted prices onto beans. Product URLs
are canonicalised to the no-collection ``/products/<handle>`` form used by the
live site (verified against sitemap_products_1.xml).
"""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="sorcery",
    display_name="Sorcery Coffee Roasters",
    roaster_name="Sorcery Coffee Roasters",
    website="https://sorcerycoffee.co.za",
    description="Pretoria, South Africa light-roast specialty coffee roaster with cafés in "
    "Hillcrest and Wapadrand, roasting single origins from a Shopify "
    "storefront priced in ZAR",
    requires_api_key=True,
    currency="ZAR",
    country="South Africa",
    status="available",
)
class SorceryScraper(ShopifyJsonScraper):
    """Scraper for Sorcery Coffee Roasters (sorcerycoffee.co.za) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Sorcery Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Sorcery Coffee Roasters",
            base_url="https://sorcerycoffee.co.za",
            products_json_urls=[
                "https://sorcerycoffee.co.za/collections/all/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Pin the store currency to the home-market ZAR. The site runs
        # Shopify Markets currency geolocation; a datacenter IP may receive
        # converted prices, so the geo-detected value must never override ZAR.
        self.store_currency = "ZAR"
        self._currency_detected = True

        # The full catalogue is 7 bean coffees plus a compostable-pods
        # product (single-serve capsule format, not whole beans). Genuine
        # tasting kits/samplers are NOT excluded — the base
        # ``_apply_product_flags`` pipeline flags them for admin review.
        self.exclude_slugs = [
            "pods",
            "capsule",
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

        Sorcery Coffee Roasters is a South African roaster priced in ZAR (the
        products.json prices are ZAR). The site serves a geo-localized
        presentment currency via Shopify Markets based on the caller's IP,
        which would otherwise override the correct base currency during
        extraction. Force ZAR so the AI prices the beans correctly.
        """
        return "ZAR"

    def postprocess_extracted_bean(self, bean):
        """Force the bean currency to ZAR (store base currency)."""
        bean = super().postprocess_extracted_bean(bean)
        bean.currency = "ZAR"
        return bean

    def preprocess_product_url(self, url: str) -> str:
        """Strip the collection segment from product URLs.

        Sorcery's canonical product pages are just ``/products/<handle>``
        (no collection prefix), so remove the ``/collections/<name>/``
        added by the Shopify base from the collection products.json URLs.
        """
        return re.sub(r"/collections/[^/]+/products/", "/products/", url)
