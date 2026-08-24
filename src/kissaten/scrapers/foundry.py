"""Foundry Coffee Roasters scraper implementation with Shopify JSON extraction.

Foundry Coffee Roasters (foundrycoffeeroasters.com) is a Shopify-hosted
specialty roaster in Sheffield, United Kingdom. The curated ``coffee-beans``
collection (All Our Coffee Beans) carries exactly the beans — 9 products,
all with ``product_type`` "Coffee Beans" (verified 2026-08): Villa Pastora
Colombia, Imbalu Uganda, Kii AA Kenya, El Indio Colombia, Etiopia Gesha El
Salvador, Yulieth Mora Colombia, No. 9 Roast, Coproca Rwanda, and Popayan
Decaf Colombia. ``/collections/all`` is deliberately avoided: it mixes in
green coffee, gear, and non-coffee categories.

The products.json ``body_html`` is dense prose (550–1300 chars per bean)
carrying the tasting notes, origin hints, and processing detail; the rendered
product pages add nothing beyond that (no spec-sheet, no cupping score, no
schema.org bean fields, no accordion/carousel content — the page is a
JS-rendered theme whose description only exists in the embedded storefront
JSON), so the scraper runs JSON-only (``scrape_product_pages=False``,
``use_optimized_mode=True``) on the injected Shopify context.

Product URLs canonicalize to ``/products/<handle>`` (the site's real product
URL form), so ``preprocess_product_url`` strips the collection segment. Shop
currency is pinned to GBP so a geo-localized storefront can't stamp
converted prices.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="foundry",
    display_name="Foundry Coffee Roasters",
    roaster_name="Foundry",
    website="https://foundrycoffeeroasters.com",
    description="Specialty coffee roaster based in Sheffield, UK, known for "
    "adventurous single-origin coffees and a classic house espresso blend.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class FoundryScraper(ShopifyJsonScraper):
    """Scraper for Foundry Coffee Roasters (foundrycoffeeroasters.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Foundry Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Foundry",
            base_url="https://foundrycoffeeroasters.com",
            products_json_urls=["https://foundrycoffeeroasters.com/collections/coffee-beans/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The curated coffee-beans collection is purely coffee; the rendered
        # page adds nothing over the JSON context. Pin GBP so Shopify's
        # geo-localized price conversion can't rewrite the prices.
        self.store_currency = "GBP"
        self._currency_detected = True

        # No tasting-kit/sampler products exist in this collection — the base
        # _apply_product_flags handles any future ones. Only keep the standard
        # genuine-equipment/service safety net for a curated collection.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Strip the collection segment; Foundry canonicalizes to ``/products/<handle>``.

        ShopifyJsonScraper builds ``/collections/coffee-beans/products/<handle>``
        from the products.json base, but the site serves canonical product pages
        at ``/products/<handle>`` (verified via the ``rel=canonical`` link on
        both forms). Using the canonical form keeps history keyed to the real URLs.
        """
        return f"{self.base_url}/products/{url.rstrip('/').split('/products/')[-1].split('?')[0]}"
