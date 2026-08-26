"""Papercup Coffee scraper implementation with Shopify JSON extraction.

Papercup Coffee (papercupcoffee.co.uk) is a London specialty coffee roaster on
Shopify. The site canonicalizes to the ``www`` subdomain
(``papercupcoffee.co.uk`` 301 → ``www.papercupcoffee.co.uk``). Its curated
``beans`` collection is the whole-bean offering — ~12 published products, all
typed ``Beans`` and titled with a bean name (e.g. ``Fruit Salad, Colombia``),
making it the entire coffee catalogue.

The Shopify ``body_html`` carries the bean details the ``CoffeeBean`` schema
needs (origin, region, varietal, altitude, process, tasting notes, roast
level), so the cheapest JSON-only path is used: ``scrape_product_pages=False``
with ``use_optimized_mode=True`` and no page caching. The rendered product page
adds nothing beyond JSON-LD that mirrors the product JSON.

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
    name="papercup",
    display_name="Papercup Coffee",
    roaster_name="Papercup Coffee",
    website="https://www.papercupcoffee.co.uk",
    description="London specialty coffee roaster offering a curated collection "
    "of whole-bean coffees, from exotic single origins and natural "
    "fermentations to espresso blends and decaf.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class PapercupCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Papercup Coffee (papercupcoffee.co.uk) using Shopify products.json.

    Uses the curated ``beans`` collection, which is the roaster's whole-bean
    coffee catalogue, rather than ``collections/all`` (which would mix in
    non-coffee items).
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Papercup Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Papercup Coffee",
            base_url="https://www.papercupcoffee.co.uk",
            products_json_urls=[
                "https://www.papercupcoffee.co.uk/collections/beans/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Papercup is a UK store priced in GBP. The storefront can geolocate the
        # datacenter IP to a non-GBP market, so pin the home currency and mark it
        # as detected to skip the collection-page currency-detection path.
        self.store_currency = "GBP"
        self._currency_detected = True

        # The curated ``beans`` collection holds only whole-bean products, so no
        # sampler / taster-pack slugs are excluded here: the base class flags
        # tasting kits (flag-don't-exclude) so they land in the admin review
        # queue rather than being dropped. Keep a conservative list of genuine
        # non-coffee categories as a safety net should any slip into the
        # collection later.
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
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Papercup product URLs.

        The live site canonicalizes product pages to the no-collection form
        ``/products/<handle>`` (confirmed via ``rel=canonical`` and ``og:url``),
        so strip the ``/collections/<slug>`` segment that the products.json base
        URL injects.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
