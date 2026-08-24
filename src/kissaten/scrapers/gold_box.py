"""Gold Box Coffee Roasters scraper implementation with Shopify JSON extraction.

Gold Box ("Gold Box Roastery LLC" / "Gold Box Coffee Roasters") is a roastery
with UK (6-8 Vance Court, Transbritannia Enterprise Park, Blaydon, Newcastle
upon Tyne NE21 5NH) and Dubai operations; this reviewed storefront operates
from Dubai and sells in AED (``shop_currency: "AED"``, prices shown as Dhs.).
The curated ``coffee`` collection publishes 41 coffee products (Discovery
Taster Box, Experimental Taster Box, Arabic Gahwa, blends, single origins and
competition-series geishas at 110-175 Dhs.).

The Discovery/Experimental Taster Boxes ARE curated tasting kits — they must
NOT be excluded. They are extracted and flagged ``is_tasting_kit`` /
``requires_review`` by ``_apply_product_flags`` into the admin review queue.
The base kit patterns match ``taster-pack``/``sample-pack`` but not
``taster-box``, so ``_get_tasting_kit_url_patterns`` is overridden to add
``taster-box``.

Shape: the Shopify ``body_html`` is rich for the competition lots / geishas
(carries Origin, Producer, Farm, Variety, Process, Altitude, Roast Profile and
In-the-Cup tasting notes) and the AI extracts from that injected JSON context,
so the scraper is JSON-only (``scrape_product_pages=False``) with
``use_optimized_mode=True`` — the token-cheapest option that still captures
every bean field.

Canonical URLs are the no-collection ``/products/<handle>`` form (verified via
``rel=canonical`` on a live product page), so ``preprocess_product_url`` strips
the collection segment the collection products.json base otherwise produces.

Currency is pinned to AED (verified ``shop_currency: "AED"`` on the live
payload) and ``_currency_detected`` is set in ``__init__`` so no
geo-detection can override it.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="gold-box",
    display_name="Gold Box",
    roaster_name="Gold Box",
    website="https://goldboxroastery.com",
    description="Specialty coffee roastery with UK (Blaydon, Newcastle) and Dubai "
    "operations; this storefront is the Dubai (AED) shop, offering single origins, "
    "blends and competition-series geishas",
    requires_api_key=True,
    currency="AED",
    country="United Arab Emirates",
    status="available",
)
class GoldBoxScraper(ShopifyJsonScraper):
    """Scraper for Gold Box Coffee Roasters (goldboxroastery.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Gold Box scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Gold Box",
            base_url="https://goldboxroastery.com",
            products_json_urls=["https://goldboxroastery.com/collections/coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Exclude genuine non-coffee products. Deliberately NOT excluded: the
        # Discovery / Experimental Taster Boxes — they are curated tasting kits
        # and must flow through to the admin review queue (flagged by
        # _apply_product_flags), not be dropped.
        self.exclude_slugs = [
            "subscription",
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
            "training",
            "work-wear",
        ]

        # Store serves AED natively; pin defensively (geo-detected currency
        # must never override the home-market AED prices).
        self.store_currency = "AED"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def _get_excluded_url_patterns(self) -> list[str]:
        """Drop the generic ``discovery`` exclusion for this roaster.

        The base pattern list uses ``"discovery"`` to skip "Discovery"-branded
        subscription boxes on other roasters, but Gold Box's only ``discovery``
        product is the **Discovery Taster Box** — a curated coffee tasting kit
        (handle ``discovery-taster-box``) that must be extracted and flagged
        ``is_tasting_kit``/``requires_review``, not silently dropped. Removing
        ``"discovery"`` here lets it flow through to the admin review queue.
        """
        return [p for p in super()._get_excluded_url_patterns() if p != "discovery"]

    def _get_tasting_kit_url_patterns(self) -> list[str]:
        """Add Gold Box's taster-box URL token to the base kit patterns.

        The base patterns match ``taster-pack`` / ``sample-pack`` style
        handles but not the store's ``taster-box`` handles (``discovery-taster-box``,
        ``experimental-taster-box-1``), so extend with ``taster-box`` to ensure
        both curated Taster Boxes are flagged and sent for admin review.
        """
        return super()._get_tasting_kit_url_patterns() + ["taster-box"]

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Gold Box product URLs to the canonical form.

        Gold Box's canonical/live product pages are the no-collection form
        ``/products/<handle>`` (verified via ``rel=canonical`` on a live product
        page). The collection products.json base URL produces the
        collection-prefixed form, so strip any collection segment here.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
