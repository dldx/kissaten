"""Hundred House Coffee scraper implementation with Shopify JSON extraction.

Hundred House Coffee (hundredhousecoffee.com) is a UK specialty coffee
roastery based on the Shropshire/North Wales border, on Shopify. Verified
live 2026-08-18:

Collections
-----------
* ``/collections/allcoffees/products.json`` — the curated "All Coffees"
  umbrella collection. ``products.json`` returns 16 published products (the
  Shopify nav counter shows 27, but ``products.json`` is authoritative for
  the live crawl set): 10 single origins, 5 blends, and 2 coffee bundles.
  It is the single crawl source — ``/collections/all`` is avoided on
  purpose and the sibling ``single-origins-*`` collections (``single-origins-all``
  10, ``new-site-single-origins`` 4, ``single-origins-experimental-copy`` 7)
  are all subsets of it.

Currency
--------
GBP (``Shopify.currency.active == "GBP"``, rate 1.0), pinned in ``__init__``
so Shopify's geolocated market conversion can't stamp caller-market prices
onto the beans.

Shape
-----
JSON-only + optimized mode. The products.json ``body_html`` carries a dense
structured spec table for singles (FARM, REGION, ALTITUDE, VARIETAL,
PROCESS, FLAVOUR NOTES) and tasting-note paragraphs for blends, and the
variants encode the weight (227g/1KG) and grind options with GBP prices.
The rendered product page adds no roast level, cupping score, or other
bean-specific field the JSON lacks, so page scraping is skipped entirely.

Canonical URL
-------------
Product URLs canonicalise to ``/products/<handle>`` (Shopify's
``<link rel="canonical">`` points at the no-collection form, which serves
200 and is what the site links). ``preprocess_product_url`` strips any
collection segment so the scraper uses the canonical form throughout.

Kits
----
Two products bundle multiple coffees: "Rwanda Special: 3 Bags for £30 +
Limited Edition Riso Print" (``rwanda-special-three-bags-for-a-limited-edition-riso-print``)
and "Freak & Unique XX and XXI" (``freak-unique-bundle``). They carry no
standard tasting-kit token, so ``postprocess_review_flags`` marks them
``is_tasting_kit`` to land them in the admin review queue rather than
silently dropping them.
"""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="hundred-house",
    display_name="Hundred House Coffee",
    roaster_name="Hundred House",
    website="https://hundredhousecoffee.com",
    description="UK specialty coffee roastery (Shropshire/North Wales border) "
    "roasting single origins, blends and decaf with a focus on "
    "traceability and distinctive processing.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class HundredHouseScraper(ShopifyJsonScraper):
    """Scraper for Hundred House Coffee (hundredhousecoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize the Hundred House Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Hundred House",
            base_url="https://hundredhousecoffee.com",
            products_json_urls=[
                "https://hundredhousecoffee.com/collections/allcoffees/products.json",
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

        # The curated allcoffees collection is mostly pure coffee, so most of
        # this list is a safety net for future catalogue additions rather
        # than an active filter. The one active exclusion: the four "ns-"
        # prefixed handles (ns-bon-bon, ns-nom-nom-copy, ns-coco,
        # ns-vida-organic) are non-coffee ready-to-drink no-sugar canned
        # drinks rather than beans; they persistently fail AI extraction, so
        # they are filtered at discovery by exact handle. A bare "ns-" prefix
        # is deliberately NOT used - the store also reuses "ns-" for genuine
        # coffee pages (e.g. ns-about, ns-26-*) - so precise handle patterns
        # keep any real coffee that shows up flowing through.
        # NOTE: tasting-kit / sampler / taster tokens are intentionally NOT
        # listed - any coffee tasting set or bundle that shows up flows
        # through and gets flagged for review via _apply_product_flags /
        # postprocess_review_flags.
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
            # Non-coffee ready-to-drink no-sugar canned drinks (not beans),
            # matched by exact handle so discovery filters them out before
            # the AI extraction step.
            "ns-bon-bon",
            "ns-nom-nom-copy",
            "ns-coco",
            "ns-vida-organic",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Canonicalize hundredhousecoffee.com product URLs to ``/products/<handle>``.

        The site serves each product at both
        ``/collections/<name>/products/<handle>`` and ``/products/<handle>``;
        the no-collection form is canonical (Shopify's canonical link tag
        points at ``https://hundredhousecoffee.com/products/<handle>``), so
        any collection segment is stripped.
        """
        match = re.search(r"^(https?://[^/]+)/.*/products/(.+)$", url)
        if match:
            return f"{match.group(1)}/products/{match.group(2)}"
        return url

    def postprocess_review_flags(self, bean, url: str):
        """Flag Hundred House's multi-bag coffee bundles for admin review.

        "Rwanda Special: 3 Bags for £30 + Limited Edition Riso Print" and
        "Freak & Unique XX and XXI" bundle two or more coffees but carry no
        standard tasting-kit token in their handles, so the base
        heuristics miss them. Mark them ``is_tasting_kit`` here so they land
        in the admin review queue instead of being shown to the public.
        """
        if any(tok in url for tok in ("rwanda-special-three-bags", "freak-unique-bundle")):
            bean.is_tasting_kit = True
        return bean
