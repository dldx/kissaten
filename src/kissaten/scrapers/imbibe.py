"""Imbibe Coffee Roasters scraper implementation with Shopify JSON extraction.

Imbibe Coffee Roasters (imbibe.ie) is an Irish specialty coffee roaster based
in Dublin, selling whole-bean single origins, blends and decaf. The store is
Shopify-hosted and prices its products in EUR (€) for the Irish market.

The curated ``/collections/all-coffees`` collection carries the whole-bean
catalogue (single origins, blends, decaf and the rotating "Two To Go Bundle"
two-coffee sampler); equipment, gift boxes and vouchers live outside it. The
``body_html`` of the products.json carries structured ``Process:`` /
``Varietal:`` / ``Altitude:`` / ``Tasting notes:`` labels plus descriptive
prose, and the variants carry the weight/price options, so pure JSON-only
extraction (``scrape_product_pages=False``) is sufficient.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="imbibe",
    display_name="Imbibe Coffee Roasters",
    roaster_name="Imbibe Coffee Roasters",
    website="https://imbibe.ie",
    description="Irish specialty coffee roaster based in Dublin (Shopify).",
    requires_api_key=True,
    currency="EUR",  # Irish market; € pricing confirmed on the storefront
    country="Republic of Ireland",
    status="available",
)
class ImbibeScraper(ShopifyJsonScraper):
    """Scraper for Imbibe Coffee Roasters (imbibe.ie) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize the Imbibe Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Imbibe Coffee Roasters",
            base_url="https://imbibe.ie",
            products_json_urls=[
                "https://imbibe.ie/collections/all-coffees/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # The all-coffees collection is curated to whole-bean coffee, but keep
        # defensive exclusions for any equipment/services that sneak in. The
        # "Two To Go Bundle" sampler must NOT be excluded — it is flagged as a
        # tasting kit via postprocess_review_flags instead (see KIT_REVIEW.md).
        self.exclude_slugs = [
            "gift-card",
            "giftcard",
            "voucher",
            "subscription",
            "equipment",
            "grinder",
            "filter",
            "aeropress",
            "hario",
            "merch",
        ]

        # The storefront prices in EUR for the Irish market (€ symbols and
        # EUR throughout the storefront; no GBP). Pin the store currency and
        # mark it as detected so the collection-page detection path in
        # _scrape_new_products is skipped.
        self.store_currency = "EUR"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Normalize product URLs to ``/products/<handle>`` by stripping collection segments."""
        return url.replace("/collections/all-coffees", "")

    def postprocess_review_flags(self, bean, url: str):
        """Flag the rotating multi-coffee bundle as a tasting kit for review.

        The "Two To Go Bundle" (handle ``new-bundle-2``) is a curated
        two-coffee sampler — two single origins from the current list at a
        discount, rotating regularly. It is treated like a tasting kit: kept
        in the catalogue but routed to the admin review queue
        (``requires_review``) instead of public search. No single-origin bean
        handle carries the "bundle" token.
        """
        if bean is not None and "bundle" in str(url).lower():
            bean.is_tasting_kit = True
        return bean
