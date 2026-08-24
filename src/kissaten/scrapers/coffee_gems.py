"""Coffee Gems scraper implementation with Shopify JSON extraction.

Coffee Gems (coffeegems.co.uk) is a UK (Huddersfield) specialty coffee
roaster on Shopify. The site is organised around many overlapping curated
collections, so we merge two coffee-specific ``products.json`` endpoints:

* ``/collections/coffee/products.json`` — the curated "Coffee" collection
  (16 products) that is the umbrella for blends + single origins + decafs
  (it already includes the competition coffees: FINCA ZARZA, CERRO AZUL,
  LAS MARGARITAS). This is the clean pure-coffee core.
* ``/collections/coffee-blends/products.json`` — adds the NONNA EMMA blend
  (a genuine bean missing from the curated collection) plus the two
  espresso/decaf "Taster Trio" coffee tasting kits.

Merging these two keeps blends, single origins and decafs covered while
leaving equipment, gift sets, machines, vouchers, experiences and
accessories out (they live in other collections we never crawl). Products
that appear in both collections are deduplicated by the base class on the
canonical product URL.

Kit handling: the Taster Trio collections are curated coffee bean tasting
sets (three 80g bags), NOT exclusions — the base ``_apply_product_flags``
flags them ``is_tasting_kit`` / ``requires_review`` (the handle carries the
"taster" token) so they land in the admin review queue instead of being
dropped or shown publicly. Genuine services (vouchers, experiences,
subscriptions) and non-bean items (Cascara Crunch fruit snack, drippers,
machines, containers) are excluded via ``exclude_slugs``.

Currency: GBP (``Shopify.currency.active == "GBP"``), pinned in
``__init__`` so Shopify's geolocated market conversion can't override it.

Shape: JSON-only + optimized mode. The ``body_html`` carried by the
products.json payload is dense (origin, process, variety, tasting notes and
roast all present), so we skip fetching product pages entirely.

Canonical URL: the site serves products at both
``/collections/<name>/products/<handle>`` and ``/products/<handle>`` — the
no-collection form is canonical (Shopify redirects the collection-prefixed
URL to it), so ``preprocess_product_url`` strips the collection segment.
"""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="coffee-gems",
    display_name="Coffee Gems",
    roaster_name="Coffee Gems",
    website="https://coffeegems.co.uk",
    description="UK specialty coffee roaster (Huddersfield) known for curated "
    "single origins, blends and decafs, with a strong focus on competition coffees.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class CoffeeGemsScraper(ShopifyJsonScraper):
    """Scraper for Coffee Gems (coffeegems.co.uk) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize the Coffee Gems scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Coffee Gems",
            base_url="https://coffeegems.co.uk",
            products_json_urls=[
                "https://coffeegems.co.uk/collections/coffee/products.json",
                "https://coffeegems.co.uk/collections/coffee-blends/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Pin GBP so Shopify's geolocated market conversion can't stamp
        # caller-market prices onto the beans (confirmed GBP in page HTML:
        # Shopify.currency = {"active":"GBP","rate":"1.0"}).
        self.store_currency = "GBP"
        self._currency_detected = True

        # Genuine non-coffee products. NOTE: tasting-kit / taster tokens
        # (e.g. "taster-trio-collection-*") are intentionally NOT listed here
        # - any coffee tasting set flows through and gets flagged for review.
        # "dripper" is also excluded by the base URL patterns; we keep the
        # list explicit for the non-bean items that leak in from coffee-blends.
        self.exclude_slugs = [
            "cascara",  # Cascara Crunch - coffee cherry fruit snack, not beans
            "voucher",  # coffee gift experience vouchers (services)
            "experience",  # coffee experiences / masterclasses (services)
            "subscription",  # recurring gift subscription plans
            "gift-card",  # gift cards
            "gift-box",  # non-bean gift boxes (equipment bundles)
            "machine",  # espresso / coffee machines
            "container",  # storage containers
            "mug",
            "tote",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Canonicalize coffeegems.co.uk product URLs to ``/products/<handle>``.

        The site serves each product at both
        ``/collections/<name>/products/<handle>`` and ``/products/<handle>``;
        the no-collection form is canonical (Shopify redirects the
        collection-prefixed URL to it), so we strip any collection segment.
        """
        match = re.search(r"^(https?://[^/]+)/.*/products/(.+)$", url)
        if match:
            return f"{match.group(1)}/products/{match.group(2)}"
        return url
