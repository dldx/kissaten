"""Heartland Coffee Roasters scraper implementation with Shopify JSON extraction.

Heartland Coffee Roasters (heartland.coffee) is a UK (North Wales) specialty
coffee roaster on Shopify (roasters-wales.myshopify.com). Verified live
2026-08-18:

Collections
-----------
* ``/collections/coffee/products.json`` — the curated "Coffee" collection
  (19 products) that is the umbrella for single origins + blends + decaf.
  All 19 entries are genuine beans (17 single origins, the Landmark blend
  and the Swiss Water decaf blend); no equipment/merch leaks in. This is
  the single crawl source — ``/collections/all`` is avoided on purpose and
  the sibling ``/collections/single-origin`` (17 products, all a subset of
  the coffee collection) is not crawled separately.

Currency
--------
GBP (``Shopify.currency.active == "GBP"``, rate 1.0), pinned in ``__init__``
so Shopify's geolocated market conversion can't stamp caller-market prices
onto the beans.

Shape
-----
JSON-only + optimized mode. The products.json ``body_html`` carries a dense
structured spec table (Country, Region, Producer, Altitude, Varietal,
Process, Cupping Notes; blends use "Countries") plus variants encoding the
weight (250g/500g/1kg) and grind options with GBP prices. The rendered
product page adds only a generic region blurb (shared across all coffees
from the same region) and no bean-specific fields the JSON lacks, so page
scraping is skipped entirely.

Canonical URL
-------------
The store is served at both heartlandcoffee.co.uk and heartland.coffee;
heartlandcoffee.co.uk 301-redirects to heartland.coffee, which is the
canonical domain (the ``<link rel="canonical">`` on every product points at
``https://heartland.coffee/products/<handle>``). Product URLs canonicalise
to the no-collection form, so ``preprocess_product_url`` strips the
collection segment and the scraper uses heartland.coffee URLs throughout.
"""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="heartland-coffee",
    display_name="Heartland Coffee Roasters",
    roaster_name="Heartland Coffee Roasters",
    website="https://heartland.coffee",
    description="UK specialty coffee roaster (North Wales) roasting single "
    "origins, blends and Swiss Water decaf with a focus on quality "
    "and traceability.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class HeartlandCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Heartland Coffee Roasters (heartland.coffee) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize the Heartland Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Heartland Coffee Roasters",
            base_url="https://heartland.coffee",
            products_json_urls=[
                "https://heartland.coffee/collections/coffee/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Pin GBP so Shopify's geolocated market conversion can't stamp
        # caller-market prices onto the beans (confirmed in page HTML:
        # Shopify.currency = {"active":"GBP","rate":"1.0"}).
        self.store_currency = "GBP"
        self._currency_detected = True

        # The curated coffee collection is pure beans, so this is a safety
        # net for future catalogue additions rather than an active filter.
        # NOTE: tasting-kit / sampler / taster tokens are intentionally NOT
        # listed - any coffee tasting set that shows up flows through and
        # gets flagged for review via _apply_product_flags.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
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
        """Canonicalize heartland.coffee product URLs to ``/products/<handle>``.

        The site serves each product at both
        ``/collections/<name>/products/<handle>`` and ``/products/<handle>``;
        the no-collection form is canonical (Shopify's canonical link tag and
        heartlandcoffee.co.uk's 301 both point at
        ``https://heartland.coffee/products/<handle>``), so any collection
        segment is stripped.
        """
        match = re.search(r"^(https?://[^/]+)/.*/products/(.+)$", url)
        if match:
            return f"{match.group(1)}/products/{match.group(2)}"
        return url
