"""Perception Coffee scraper implementation with Shopify JSON extraction.

Perception Coffee (perceptioncoffee.co.uk) is a small UK specialty coffee
roaster based in South London (founded by Ali in Brixton). The roasted-bean
catalogue is tiny — a curated ``single-origin-coffees`` collection holds the
four currently published whole-bean coffees:

* BRAZIL Odair Jose (``brazil-dos-teixerias``)
* BRAZIL x EL SALVADOR (``brazil-x-el-salvador``)
* COLOMBIA Finca Los Nogales (``colombia-finca-los-nogales``)
* EL SALVADOR El Borbollon 200g (``el-salvador-el-borbollon-copy``)

The ``blends`` and ``coffee-selection`` collections surface the same products
as the single-origin collection (no additional unique handles), so merging
``single-origin-coffees`` with ``blends`` yields the full whole-bean set; the
base ``discover_all_product_urls`` deduplicates products that appear in more
than one collection (e.g. ``brazil-x-el-salvador``) to their canonical URL.

Every product's Shopify ``body_html`` carries the bean details the
``CoffeeBean`` schema needs (farm, altitude, region, varietal, process, tasting
notes), so the cheapest JSON-only path is used: ``scrape_product_pages=False``
with ``use_optimized_mode=True`` and no page caching. The rendered product page
adds nothing beyond JSON-LD that mirrors the product JSON.

The store is priced in GBP and the storefront can geolocate a datacenter IP to
a non-GBP market, so the home currency is pinned and marked as detected. The
live site serves product URLs as the no-collection form ``/products/<handle>``
(confirmed via ``rel=canonical`` / ``og:url``), so the collection segment built
from the products.json base is stripped in ``preprocess_product_url``.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="perception",
    display_name="Perception Coffee",
    roaster_name="Perception Coffee",
    website="https://www.perceptioncoffee.co.uk",
    description="South London specialty coffee roaster founded in Brixton, "
    "using coffee education and skill-building to create opportunities for "
    "young people, with a small curated single-origin and blend range.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class PerceptionCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Perception Coffee (perceptioncoffee.co.uk) using Shopify products.json.

    Uses the curated ``single-origin-coffees`` and ``blends`` collections rather
    than ``collections/all``, which also mixes in a digital guide and merch
    (t-shirts). The catalogue is tiny — four published whole-bean coffees — so
    the merge yields the full set with no non-coffee products.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Perception Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Perception Coffee",
            base_url="https://www.perceptioncoffee.co.uk",
            products_json_urls=[
                "https://www.perceptioncoffee.co.uk/collections/single-origin-coffees/products.json",
                "https://www.perceptioncoffee.co.uk/collections/blends/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Perception Coffee is a UK store priced in GBP. The storefront can
        # geolocate the datacenter IP to a non-GBP market, so pin the home
        # currency and mark it as detected to skip the collection-page
        # currency-detection path.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Exclude genuine non-coffee products only. The curated collections
        # already avoid merch / equipment, but keep a focused guard for the
        # shop's handful of non-bean items. Do NOT exclude sampler / taster-pack
        # slugs here: the base class flags tasting kits so they land in the
        # admin review queue rather than being dropped.
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
            "t-shirt",
            "tshirt",
            "mug",
            "tumbler",
            "hoodie",
            "capsules",
            "pods",
            "cold-brew-cans",
            "easy-pour",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Perception Coffee product URLs.

        The live site canonicalizes product pages to the no-collection form
        ``/products/<handle>`` (confirmed via ``rel=canonical`` and
        ``og:url``), so strip the ``/collections/<slug>`` segment that each
        products.json base URL injects. This also makes the same product
        surfacing in multiple collections (e.g. ``brazil-x-el-salvador`` in
        both ``single-origin-coffees`` and ``blends``) map to one canonical
        URL, which is what lets the merge + dedup count it exactly once.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
