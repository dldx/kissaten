"""Red Bank Coffee scraper implementation with Shopify JSON extraction.

Red Bank Coffee (redbankcoffee.com) is a UK specialty coffee roaster on
Shopify. The site nav's dedicated ``our-coffees`` collection curates the
whole-bean catalogue (14 published products as of the 2026-08 probe; the
collection page claims 16 but ``products.json`` returns only the published
14), so the scraper targets that collection rather than ``collections/all``,
which would mix in brewing equipment, mugs, caps and gift cards.

The Shopify ``body_html`` carries the tasting-note and description detail the
``CoffeeBean`` schema needs, so the cheapest JSON-only path is used:
``scrape_product_pages=False`` with ``use_optimized_mode=True`` and no page
caching. The rendered product page adds nothing beyond JSON-LD that mirrors
the product JSON.

Canonical product URLs are the no-collection form ``/products/<handle>``
(confirmed via the page ``rel=canonical`` / ``og:url``), so the collection
segment built from the products.json base is stripped in
``preprocess_product_url``.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="red-bank",
    display_name="Red Bank Coffee",
    roaster_name="Red Bank Coffee",
    website="https://www.redbankcoffee.com",
    description="UK specialty coffee roaster from Manchester offering a "
    "rotating lineup of single origin whole-bean coffees, blends and decaf, "
    "with an emphasis on direct, traceable sourcing.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class RedBankScraper(ShopifyJsonScraper):
    """Scraper for Red Bank Coffee (redbankcoffee.com) using Shopify products.json.

    Uses the curated ``our-coffees`` collection (14 published whole-bean
    coffees) rather than ``collections/all``, which also mixes in brewing
    equipment, drinkware, apparel and gift cards.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Red Bank Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Red Bank Coffee",
            base_url="https://www.redbankcoffee.com",
            products_json_urls=[
                "https://www.redbankcoffee.com/collections/our-coffees/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Red Bank is a UK store priced in GBP. The storefront can geolocate
        # the datacenter IP to a non-GBP market, so pin the home currency and
        # mark it as detected to skip the collection-page currency-detection
        # path.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Exclude genuine non-coffee products only. Do NOT exclude sampler /
        # taster-pack slugs here: the base class flags tasting kits
        # (flag-don't-exclude) so they land in the admin review queue rather
        # than being dropped. The curated our-coffee collection contains only
        # beans, but keep a defensive list in case a non-bean is added later.
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
            "sibarist",
            "origami",
            "v60",
            "grinder",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Red Bank product URLs.

        The live site canonicalizes product pages to the no-collection form
        ``/products/<handle>`` (confirmed via ``rel=canonical`` and
        ``og:url``), so strip the ``/collections/<slug>`` segment that each
        products.json base URL injects.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
