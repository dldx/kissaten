"""Radical Roasters scraper implementation with Shopify JSON extraction.

Radical Roasters (radicalroasters.co.uk) is a UK specialty coffee roaster on
Shopify. The site nav organises the roasted-bean catalogue into several
curated collections, of which ``coffee`` is the master coffee collection:

* ``coffee`` — the full roasted-bean line-up (14 published products: 12 beans
  plus a cap and a t-shirt that are filtered out as merch)
* ``decaf-coffees`` — decaf subset (``decaf-regular``, ``decaf-deluxe``)
* ``everyday-drinking`` — everyday subset (``colombia``, ``powerhouse``,
  ``the-wizard``, ``peru-yesica-llanque``)

``decaf-coffees`` and ``everyday-drinking`` are strict subsets of ``coffee``
(verified live), so scraping only ``collections/coffee/products.json`` covers
the whole bean catalogue exactly once with no double-counting. The ``coffee``
collection is preferred over ``collections/all`` because it naturally limits
to coffee and keeps the ``exclude_slugs`` list short.

The Shopify ``body_html`` carries the bean details the ``CoffeeBean`` schema
needs (tasting notes, origin, region, producer, process, varietal), so the
cheapest JSON-only path is used: ``scrape_product_pages=False`` with
``use_optimized_mode=True`` and no page caching. The rendered product page
adds nothing beyond JSON-LD that mirrors the product JSON.

Canonical URLs are the no-collection form ``/products/<handle>`` (confirmed
via the live 200 redirect from the collection-prefixed path), so the
collection segment built from the products.json base is stripped in
``preprocess_product_url``.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="radical-roasters",
    display_name="Radical Roasters",
    roaster_name="Radical Roasters",
    website="https://radicalroasters.co.uk",
    description="UK specialty coffee roaster based in Edinburgh, roasting a "
    "mix of comforting classics and experimental co-ferments with hand-printed "
    "bag art.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class RadicalRoastersScraper(ShopifyJsonScraper):
    """Scraper for Radical Roasters (radicalroasters.co.uk) using Shopify products.json.

    Uses the ``coffee`` curated collection (the site's canonical roasted-bean
    collection) rather than ``collections/all``. ``decaf-coffees`` and
    ``everyday-drinking`` are subsets of ``coffee``, so they are not scraped
    separately (that would double-count). The two merch products in the
    collection (a cap and a t-shirt) are excluded by slug.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Radical Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Radical Roasters",
            base_url="https://radicalroasters.co.uk",
            products_json_urls=[
                "https://radicalroasters.co.uk/collections/coffee/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Radical Roasters is a UK store priced in GBP. The storefront can
        # geolocate the datacenter IP to a non-GBP market, so pin the home
        # currency and mark it as detected to skip the collection-page
        # currency-detection path.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Exclude genuine non-coffee products only. Do NOT exclude sampler /
        # taster-pack / gift-pack slugs here: the base class flags tasting
        # kits (flag-don't-exclude) so they land in the admin review queue
        # rather than being dropped.
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
            "t-shirt",
            "shirt",
            "cap",
            "capsules",
            "pods",
            "cold-brew-cans",
            "easy-pour",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Radical Roasters product URLs.

        The live site serves product pages at the no-collection form
        ``/products/<handle>``, so strip the ``/collections/<slug>`` segment
        that the products.json base URL injects. This also makes any product
        surfacing in multiple collections map to one canonical URL, which is
        what keeps the count exact.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
