"""Rafiki Coffee scraper implementation with Shopify JSON extraction.

Rafiki Coffee (Edinburgh, UK) runs a Shopify storefront at rafikicoffee.com.
The live storefront succeeds the Tanifiki café (44 Portobello High Street,
Edinburgh) — this scraper is scraped under the checklist "Tanifiki" row.

The curated ``coffee-beans`` collection's products.json only exposes a subset
of the whole-bean catalogue (it omits "Roaster's Choice"), so we pull from
``collections/all`` and filter down to whole-bean coffees via ``exclude_slugs``
(cold brew, tonic, wholesale nitro, tote bag). The store sells whole beans in
GBP from the UK market.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="rafiki-coffee",
    display_name="Rafiki Coffee",
    roaster_name="Rafiki Coffee",
    website="https://rafikicoffee.com",
    description="Edinburgh specialty coffee roaster with Rwandan, Burundian "
    "single origins and a rotating seasonal menu of small-batch whole-bean "
    "coffees. Succeeds the Tanifiki café; scraped under the checklist Tanifiki row.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class RafikiCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Rafiki Coffee (rafikicoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Rafiki Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Rafiki Coffee",
            base_url="https://rafikicoffee.com",
            products_json_urls=["https://rafikicoffee.com/collections/all/products.json"],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The storefront serves the UK market (GBP). Pin GBP so a geo-localized
        # storefront (which Shopify can serve to non-UK clients) can't convert
        # prices to the caller's currency.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Exclude non-whole-bean products: cold-brew cans, the sparkling
        # tonic, wholesale cold-brew listing, and the tote-bag merch. Samplers /
        # tasting kits are NOT excluded — they are flagged for review instead.
        self.exclude_slugs = [
            "cold-brew",
            "tonic",
            "wholesale",
            "tote-bag",
            "subscription",
            "gift-card",
            "gift",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "mug",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Strip the collection segment to the canonical ``/products/<handle>`` form.

        Rafiki's canonical product URLs are ``/products/<handle>`` (no collection
        segment). ShopifyJsonScraper builds collection-prefixed URLs from the
        products.json base, so collapse ``/collections/all/products/...`` to the
        canonical no-collection form the site actually serves.
        """
        return url.replace("/collections/all/products/", "/products/")
