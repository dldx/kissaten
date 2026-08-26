"""Salford Roasters scraper implementation with Shopify JSON extraction.

Salford Roasters (salfordroasters.co.uk) is a UK coffee roaster on Shopify.
The roasted-bean catalogue is organised into five curated collections that
mirror the site nav:

* ``single-origin`` — single-origin coffees (9 published beans)
* ``espresso`` — espresso blends and espresso-friendly origins (16)
* ``filter`` — filter coffees (13)
* ``blends`` — the blend range (7)
* ``decaffinated`` — decaffeinated / low-caff coffees (5; the collection slug
  has the site's own "decaffinated" typo)

The collections overlap heavily (most single origins double as espresso /
filter options), so the base ``discover_all_product_urls`` deduplicates
products to the canonical ``/products/<handle>`` URL. The effective union is
18 unique roasted-coffee products (the ``random-coffee-subscription`` handle
is excluded as a subscription).

The Shopify ``body_html`` carries the bean details the ``CoffeeBean`` schema
needs (tasting notes, origin, process, roast), so the cheapest JSON-only path
is used: ``scrape_product_pages=False`` with ``use_optimized_mode=True`` and no
page caching.

Canonical URLs are the no-collection form ``/products/<handle>`` (confirmed
via the page ``rel=canonical`` / ``og:url``), so the collection segment built
from the products.json base is stripped in ``preprocess_product_url``.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="salford-roasters",
    display_name="Salford Roasters",
    roaster_name="Salford Roasters",
    website="https://salfordroasters.co.uk",
    description="Manchester-based coffee roaster offering single origin coffees, "
    "espresso blends, filter coffees and decaffeinated options, roasted in "
    "Salford since 2012.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class SalfordRoastersScraper(ShopifyJsonScraper):
    """Scraper for Salford Roasters (salfordroasters.co.uk) using Shopify products.json.

    Uses the five curated coffee collections that mirror the roaster's own site
    nav (single origin, espresso, filter, blends, decaf) rather than
    ``collections/all``, which also mixes in sage machines, ceramics, chocolate
    and gift products.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Salford Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Salford Roasters",
            base_url="https://salfordroasters.co.uk",
            products_json_urls=[
                "https://salfordroasters.co.uk/collections/single-origin/products.json",
                "https://salfordroasters.co.uk/collections/espresso/products.json",
                "https://salfordroasters.co.uk/collections/filter/products.json",
                "https://salfordroasters.co.uk/collections/blends/products.json",
                "https://salfordroasters.co.uk/collections/decaffinated/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Salford Roasters is a UK store priced in GBP. The storefront can
        # geolocate the datacenter IP to a non-GBP market, so pin the home
        # currency and mark it as detected to skip the collection-page
        # currency-detection path.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Exclude genuine non-coffee products only. Do NOT exclude sampler /
        # taster-pack slugs here: the base class flags tasting kits
        # (flag-don't-exclude) so they land in the admin review queue rather
        # than being dropped. "subscription" (Roaster's Choice Coffee
        # Subscription) and the equipment/ceramics/chocolate merch are caught
        # via their slugs; the curated coffee collections already exclude most
        # non-coffee categories, and the base ``is_coffee_product_name``
        # catches the subscription by name as well.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "giftcard",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "merch",
            "apparel",
            "mug",
            "tumbler",
            "hoodie",
            "tshirt",
            "capsules",
            "pods",
            "cold-brew-cans",
            "easy-pour",
            "sage-machines",
            "sage-espresso-range",
            "ceramics",
            "chocolate",
            "matcha",
            "hot-choc",
            "kit",
            "gift",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Salford Roasters product URLs.

        The live site canonicalizes product pages to the no-collection form
        ``/products/<handle>`` (confirmed via ``rel=canonical`` and
        ``og:url``), so strip the ``/collections/<slug>`` segment that each
        products.json base URL injects. This also makes the same product
        surfacing in multiple collections map to one canonical URL, which is
        what lets the merge + dedup count it exactly once.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
