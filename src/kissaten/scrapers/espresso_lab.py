"""Espresso Lab Microroasters scraper implementation with Shopify JSON extraction.

Espresso Lab Microroasters (espressolabmicroroasters.com) is a Cape Town
(Woodstock) microroaster established in 2009, based at The Old Biscuit Mill,
375 Albert Road, Woodstock. This is the South African microroaster — not to
be confused with the Turkish "Espresso Lab" chain (espressolab.com) or other
foreign stores of a similar name. The store is Shopify-hosted and priced in
ZAR (the site's country/region selector serves ZAR for every market).

The site curates a dedicated ``coffee-1`` collection containing only bean
products; the equipment/sundries (grinders, aeropress, bialetti, filters,
kettles, tumblers), books and pins live in ``collections/all`` and the
``coffee-sundries`` collection, which we deliberately avoid. The
``exclude_slugs`` below are a safety net against collection drift, not the
primary filter. No tasting kits/samplers are excluded — the drip-coffee
taste pack and any future samplers are flagged by the base
``_apply_product_flags`` pipeline into the admin review queue instead.

The products.json ``body_html`` already carries the bean detail (producer,
growing altitude, botanical variety, process, tasting notes, roast date) plus
size variants, so the scraper uses JSON-only extraction
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
    name="espresso-lab",
    display_name="Espresso Lab Microroasters",
    roaster_name="Espresso Lab Microroasters",
    website="https://espressolabmicroroasters.com",
    description="Cape Town (Woodstock) microroasters established 2009 at The Old Biscuit Mill, "
    "roasting small traceable lots from a Shopify storefront priced in ZAR",
    requires_api_key=True,
    currency="ZAR",
    country="South Africa",
    status="available",
)
class EspressoLabScraper(ShopifyJsonScraper):
    """Scraper for Espresso Lab Microroasters (espressolabmicroroasters.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Espresso Lab Microroasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Espresso Lab Microroasters",
            base_url="https://espressolabmicroroasters.com",
            products_json_urls=[
                "https://espressolabmicroroasters.com/collections/coffee-1/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Pin the store currency to the home-market ZAR. The site runs
        # Shopify Markets currency geolocation (its country/region selector
        # serves ZAR for every market); a datacenter IP may receive converted
        # prices, so the geo-detected value must never override ZAR.
        self.store_currency = "ZAR"
        self._currency_detected = True

        # The curated ``coffee-1`` collection is bean-only; these slugs are a
        # safety net against the sundries (equipment, books, pins, capsules)
        # that live in ``collections/all`` leaking into it. Genuine tasting
        # kits/samplers (e.g. the drip-coffee taste pack) are NOT excluded —
        # the base ``_apply_product_flags`` pipeline flags them for review.
        self.exclude_slugs = [
            "sundries",
            "kinu",
            "grinder",
            "sibarist",
            "capsule",
            "espressolab-pin",
            "subscription",
            "gift-card",
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

        Espresso Lab Microroasters is a South African roaster priced in ZAR
        (the products.json prices are ZAR, and the site's country/region
        selector serves ZAR for every market). The site serves a
        geo-localized presentment currency via Shopify Markets based on the
        caller's IP, which would otherwise override the correct base currency
        during extraction. Force ZAR so the AI prices the beans correctly.
        """
        return "ZAR"

    def postprocess_extracted_bean(self, bean):
        """Force the bean currency to ZAR (store base currency)."""
        bean = super().postprocess_extracted_bean(bean)
        bean.currency = "ZAR"
        return bean

    def preprocess_product_url(self, url: str) -> str:
        """Strip the collection segment from product URLs.

        Espresso Lab's canonical product pages are just ``/products/<handle>``
        (no collection prefix), so remove the ``/collections/<name>/``
        added by the Shopify base from the collection products.json URLs.
        """
        return re.sub(r"/collections/[^/]+/products/", "/products/", url)
