"""La Pêche scraper implementation with Shopify JSON extraction.

La Pêche (lapechecoffee.co.uk) is a UK specialty coffee roaster on Shopify.
The catalogue is tiny and curated — 11 live products, every one typed
``Coffee`` (no subscriptions, equipment, merch or gift cards anywhere). The
line-up is dominated by co-ferments from Edinson Argote's Quebraditas farms
in Huila, Colombia (Watermelon / Strawberry / Peach) plus Tanzanian, Peruvian
and Kenyan washed single origins.

Source strategy: we use the root ``/products.json`` endpoint directly. All
three candidates — root ``products.json``, ``/collections/all/products.json``
and ``/collections/frontpage/products.json`` — return the identical 11
products (all ``product_type == "Coffee"``), so the root endpoint is the
cleanest: it is the canonical, always-present Shopify endpoint and generates
canonical ``/products/<handle>`` URLs from the base class with no collection
segment to strip. No ``exclude_slugs`` list is needed — the entire catalog is
coffee, and the base ``is_coffee_product_url`` / ``is_coffee_product_name``
filters would catch any non-bean item that sneaks in later.

Shape: JSON-only + optimized mode. The ``body_html`` carried by the
products.json payload is dense (3.5–7.4 KB per product) and already holds
Origin, Variety, Elevation, Cup Score, Process, Producer/Farm and tasting
notes, so we skip fetching product pages entirely.

Currency: GBP (``Shopify.currency = {"active":"GBP","rate":"1.0"}`` in page
HTML, ``cart_currency=GBP`` cookie on products.json), pinned in ``__init__``
so Shopify's geolocated market conversion can't override it.

Canonical URL: ``/products/<handle>`` (no collection segment). Both URL
forms serve HTTP 200 but every page's ``<link rel="canonical">`` (and the
products sitemap) point at the no-collection form, so we store that. The
root products.json base produces it directly — no ``preprocess_product_url``
override needed.

Kit handling: the two multi-bag curated collection boxes — "Summer
Co-Ferment Collection" (3 x 200g: Peach/Strawberry/Watermelon) and "The Full
Collection" (4 x 200g) — are genuine coffee tasting collections, NOT
exclusions. Their handles carry no standard tasting-kit token, so
``postprocess_review_flags`` marks them ``is_tasting_kit``; the base
``_apply_product_flags`` then sets ``requires_review`` and they land in the
admin review queue instead of public search.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="la-peche",
    display_name="La Pêche",
    roaster_name="La Pêche",
    website="https://lapechecoffee.co.uk",
    description="UK specialty coffee roaster known for co-fermented Colombian "
    "coffees from Quebraditas Coffee Farms (Huila) alongside Tanzanian, "
    "Peruvian and Kenyan washed single origins, plus curated multi-bag "
    "coffee collection boxes.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class LaPecheScraper(ShopifyJsonScraper):
    """Scraper for La Pêche (lapechecoffee.co.uk) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize the La Pêche scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="La Pêche",
            base_url="https://lapechecoffee.co.uk",
            products_json_urls=["https://lapechecoffee.co.uk/products.json"],
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

        # No exclude_slugs: the whole catalog is Coffee (11 products, verified
        # via curl 2026-08-18). The base is_coffee_product_url /
        # is_coffee_product_name filters handle any future non-bean items.

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def postprocess_review_flags(self, bean, url: str):
        """Flag La Pêche's curated multi-bag collection boxes for review.

        "Summer Co-Ferment Collection" (``the-co-ferment-collection-...``) and
        "The Full Collection" (``the-full-collection-...``) are multi-bag
        coffee tasting boxes (3 x 200g and 4 x 200g respectively) but carry no
        standard tasting-kit token in their handles, so the base heuristics
        miss them. The store reserves the ``-collection-`` handle token for
        these curated bundles (every single-bag product has a plain handle),
        so any future collection box is flagged automatically. Mark them
        ``is_tasting_kit`` here so they land in the admin review queue instead
        of being shown to the public.
        """
        if bean is not None and "-collection-" in str(url):
            bean.is_tasting_kit = True
        return bean
