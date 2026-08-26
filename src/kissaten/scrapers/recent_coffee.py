"""Recent Coffee scraper implementation with Shopify JSON extraction.

Recent Coffee (recent.coffee, canonical host) is a Leeds, UK specialty coffee
roaster on Shopify. ``recentcoffee.co.uk`` 302-redirects to the canonical
``recent.coffee`` domain, so the scraper pins the canonical host everywhere
(product JSON URLs and ``base_url``).

The store is large (326 published products, mostly equipment / syrups / tea),
so the bean catalogue is NOT captured by ``collections/all``. Instead the
whole-bean range is spread across five curated origin/blend/decaf collections
that the scraper merges with a carnival-style multi-collection union:

* ``origin-africa-middle-east`` — single origins (2 published)
* ``asia-pacific-islands`` — single origins (2 published)
* ``latin-america-carribean`` — single origins (4 published)
* ``blends`` — the espresso/house blends (6 published)
* ``decaffeinated`` — decaffeinated coffees (1 published)

Products appearing in more than one collection are deduplicated to the
canonical ``/products/<handle>`` URL by the base ``discover_all_product_urls``
(after ``preprocess_product_url`` strips the collection segment, the same
product always maps to one canonical URL).

The Shopify ``body_html`` carries the bean details the ``CoffeeBean`` schema
needs (tasting notes, origin, region, altitude, process, varietal), so the
cheapest JSON-only path is used: ``scrape_product_pages=False`` with
``use_optimized_mode=True`` and no page caching.

Note the ``latin-america-carribean`` collection slug is spelled with a double
``r`` on the live store (the common ``latin-america-caribbean`` spelling
returns an empty feed), so the scraper uses the store's own slug.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="recent-coffee",
    display_name="Recent Coffee",
    roaster_name="Recent Coffee",
    website="https://www.recent.coffee",
    description="Leeds-based coffee shop and roaster offering single origin "
    "coffees, espresso blends, half-caff and decaf, roasted with a focus on "
    "long-term producer relationships and traceability.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class RecentCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Recent Coffee (recent.coffee) using Shopify products.json.

    Uses the five curated origin/blend/decaf collections that mirror the
    roaster's own site nav rather than ``collections/all``, which is dominated
    by equipment, brewing accessories, syrups, matcha tea and gift items.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Recent Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Recent Coffee",
            base_url="https://www.recent.coffee",
            products_json_urls=[
                "https://www.recent.coffee/collections/origin-africa-middle-east/products.json",
                "https://www.recent.coffee/collections/asia-pacific-islands/products.json",
                "https://www.recent.coffee/collections/latin-america-carribean/products.json",
                "https://www.recent.coffee/collections/blends/products.json",
                "https://www.recent.coffee/collections/decaffeinated/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Recent Coffee is a UK store priced in GBP. The storefront can
        # geolocate the datacenter IP to a non-GBP market, so pin the home
        # currency and mark it as detected to skip the collection-page
        # currency-detection path.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Exclude genuine non-coffee products only. Do NOT exclude sampler /
        # taster-pack / tasting-kit slugs here: the base class flags tasting
        # kits (flag-don't-exclude) so they land in the admin review queue
        # rather than being dropped. Note the flavoured latte kit (a syrup /
        # flavour product from the Blendsmiths collaboration, not whole beans)
        # IS a genuine non-bean product, so it is excluded.
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
            "cold-brew",
            "easy-pour",
            "syrup",
            "tea",
            "matcha",
            "latte-kit",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Recent Coffee product URLs.

        The live site canonicalizes product pages to the no-collection form
        ``/products/<handle>`` (confirmed via the page ``rel=canonical`` /
        ``og:url``), so strip the ``/collections/<slug>`` segment that each
        products.json base URL injects. This also makes the same product
        surfacing in multiple collections map to one canonical URL, which is
        what lets the merge + dedup count it exactly once.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
