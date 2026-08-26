"""Mutual Coffee Roasters scraper implementation with Shopify JSON extraction.

Mutual Coffee Roasters (mutualcoffee.co.uk, canonical apex — www 301s to apex)
is an Edinburgh micro-roastery selling whole-origin coffee priced in GBP (£).
The store is Shopify-hosted behind Cloudflare with zero anti-bot, serves a
single en-GB locale and has no geo-markets, so products.json returns native
GBP prices with no market/currency conversion.

Collection selection & the wholesale-duplicate problem:
The full catalogue (``products.json``, 25 products) is a mix of 10 retail
whole-bean coffees, 11 wholesale duplicates (each coffee also published as a
separate ``product_type == "Wholesale"`` product; Shyira Natural exists ONLY
in Wholesale), 3 subscriptions (15 variants each) and 1 cap ("Mutual M Cap",
fully unavailable). The wholesale handles do NOT reliably carry a
"wholesale" token (e.g. ``kigeri-washed-burundi-1``, ``guillermo-cardona``,
``cdnt``), so slug-based exclusion cannot safely separate them. The curated
``/collections/new-coffee`` page, however, is exactly the 10 retail
whole-bean coffees with no wholesale/subscription/cap contamination
(verified 2026-08), so only that collection is scraped. Note the naive
``/collections/coffee`` handle is empty; the coffee nav collection resolves
to ``new-coffee``. The wholesale-only Shyira Natural is intentionally not
scraped — it is not part of the retail catalogue.

Shape: the products.json ``body_html`` carries the full tasting-note
description and the product title carries the origin, and the rendered
product page adds no structured bean fields the JSON lacks, so JSON-only
extraction is used (``scrape_product_pages=False``).

Canonical form: the site serves product pages at
``https://mutualcoffee.co.uk/products/<handle>`` (no collection segment), so
product URLs are normalised to that form.

Currency: base GBP with no markets, but the storefront may still geolocate
curl_cffi requests, so ``store_currency`` is pinned to GBP and marked
detected (defensive).
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="mutual",
    display_name="Mutual Coffee Roasters",
    roaster_name="Mutual Coffee Roasters",
    website="https://mutualcoffee.co.uk",
    description="Edinburgh micro-batch roastery selling single-origin whole-bean "
    "coffees sourced direct from producers, priced in GBP",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class MutualScraper(ShopifyJsonScraper):
    """Scraper for Mutual Coffee Roasters (mutualcoffee.co.uk) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize the Mutual Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Mutual Coffee Roasters",
            base_url="https://mutualcoffee.co.uk",
            products_json_urls=["https://mutualcoffee.co.uk/collections/new-coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The new-coffee collection is already pure whole-bean coffee (verified
        # 2026-08): no wholesale duplicates, no subscriptions, no cap. No slug
        # exclusions are needed here; the base class filters (URL patterns +
        # product-name categories) still guard against any non-bean product
        # that may later be added to the collection.
        self.exclude_slugs = []

        # Pin the roaster's home GBP currency and mark it as detected so the
        # collection-page currency-detection path in _scrape_new_products is
        # skipped (defensive against datacenter-IP geolocation).
        self.store_currency = "GBP"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Mutual product URLs to the canonical form.

        The site's canonical product pages are
        ``https://mutualcoffee.co.uk/products/<handle>`` (no collection
        segment), so strip the collection path built from the products.json
        URL base.
        """
        if "/collections/" in url and "/products/" in url:
            try:
                handle = url.split("/products/")[-1].split("?")[0]
                return f"{self.base_url}/products/{handle}"
            except Exception:
                return url
        return url
