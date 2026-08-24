"""Carnival Coffee Roasters scraper implementation with Shopify JSON extraction.

Carnival Coffee Roasters (carnivalcoffee.co.uk) is a London-based speciality
coffee roaster on Shopify. There is **no** master ``/collections/coffee``
(404): the whole-bean catalogue is curated across three separate collections
that must all be scraped and merged —

* ``filter-coffee`` (13 products)
* ``espresso-coffee`` (14 products)
* ``delightful-decaf`` (1 product)

Each collection is its own ``products.json`` endpoint. Because a product can
appear in more than one collection (``espresso-decaf-black-condor`` lives in
both ``espresso-coffee`` and ``delightful-decaf``), product URLs are
canonicalised to the no-collection form the live site serves
(``/products/<handle>``, confirmed via ``rel=canonical``) and the
``_shopify_product_data`` / ``_shopify_stock_status`` maps are keyed by that
canonical URL so overlapping products are counted exactly once.

The curated collections are nearly all beans, but each leaks a couple of
non-coffee items that are excluded here: brewing equipment
(``get-your-brew-on-simplify-brewer``) and two classes/workshops
(``latte-art-workshop``, ``home-espresso-workshop``). Tasting packs
(``*coffee-tasting-pack*``) are **retained** and flagged by the base class via
``_apply_product_flags`` (flag-don't-exclude) rather than silently dropped, and
named coffee bundles (``*-coffee-bundle``) are retained as coffee products.

The Shopify ``body_html`` carries the bean details the ``CoffeeBean`` schema
needs (tasting notes, mountain/elevation, variety, process, producer, origin,
roaster notes), so the cheapest JSON-only path is used:
``scrape_product_pages=False`` with ``use_optimized_mode=True``.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="carnival",
    display_name="Carnival Coffee Roasters",
    roaster_name="Carnival",
    website="https://carnivalcoffee.co.uk",
    description="London-based speciality coffee roaster known for its curated "
    "filter, espresso and decaf coffees with distinctive, fruit-forward flavour profiles",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class CarnivalScraper(ShopifyJsonScraper):
    """Scraper for Carnival Coffee Roasters (carnivalcoffee.co.uk) using Shopify products.json."""

    # Product types accepted as coffee. The collections are curated to coffee,
    # but the filter collection leaks a brewing-equipment product typed
    # "Coffee brewing equipment"; an explicit allowlist keeps only beans while
    # an exclude-slug net below handles the classes (typed "Coffee").
    _COFFEE_PRODUCT_TYPES = frozenset({"Coffee", "Speciality coffee"})

    def __init__(self, api_key: str | None = None):
        """Initialize Carnival Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Carnival",
            base_url="https://carnivalcoffee.co.uk",
            products_json_urls=[
                "https://carnivalcoffee.co.uk/collections/filter-coffee/products.json",
                "https://carnivalcoffee.co.uk/collections/espresso-coffee/products.json",
                "https://carnivalcoffee.co.uk/collections/delightful-decaf/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Exclude non-coffee products (workshops, brewing equipment, merch,
        # subscriptions, gift cards). Deliberately NOT in this list:
        # "tasting-pack"/"sample"/"sampler" (retained + flagged by the base) and
        # "bundle" (named coffee bundles are retained as coffee products).
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "brewer",
            "workshop",
            "class",
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
            "drip-bags",
        ]

        # Pin the store currency to GBP (home market). The store runs Shopify
        # Markets and can geolocate prices to the caller's IP/Accept-Language,
        # so mark currency as already detected to stop the collection-page
        # detection from overwriting it.
        self.store_currency = "GBP"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Carnival product URLs.

        Carnival's canonical/live product pages are the no-collection form
        ``/products/<handle>`` (confirmed via the page's ``rel=canonical``), so
        strip the ``/collections/<slug>`` segment that each products.json base
        URL injects. This makes the same product surfacing in multiple
        collections map to one canonical URL, which is what lets the merge +
        dedup count it exactly once.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from one curated coffee collection.

        The collections are the roaster's coffee catalogue, but each leaks a
        small number of non-coffee items, so filter on the Shopify
        ``product_type`` allowlist plus an exclude-slug net before building the
        URL. Tasting packs and coffee bundles pass through (their handles don't
        trip an exclude keyword) and are later flagged/kept by the base class.

        ``_shopify_product_data`` / ``_shopify_stock_status`` are keyed by the
        canonical (collection-stripped) URL so a product appearing in multiple
        collections is recorded once; the base ``discover_all_product_urls``
        merges the three collections and de-duplicates on that canonical form.
        """
        products = await self._fetch_all_shopify_products(store_url)
        found_urls = []

        for product in products:
            handle = product.get("handle")
            if not handle:
                continue

            # Only accept products Shopify classifies as coffee. This excludes
            # the filter collection's brewing-equipment item (typed
            # "Coffee brewing equipment") while keeping every bean.
            if product.get("product_type", "") not in self._COFFEE_PRODUCT_TYPES:
                logger.debug(f"Skipping non-coffee product type: {handle} ({product.get('product_type')})")
                continue

            # Skip explicitly excluded product slugs (matches if slug is a substring of handle).
            if any(slug in handle for slug in self.exclude_slugs):
                logger.debug(f"Skipping excluded product slug: {handle}")
                continue

            # Build product URL using the base of the products.json URL.
            base_path = store_url.replace("/products.json", "")
            url = f"{base_path}/products/{handle}"

            # Canonicalize to the no-collection form (verified live).
            url = self.preprocess_product_url(url)

            # Store metadata for later enrichment and stock status, keyed by the
            # canonical URL so cross-collection duplicates share one entry.
            self._shopify_product_data[url] = product

            # A product is in stock if any of its variants are available.
            is_available = any(v.get("available", False) for v in product.get("variants", []))
            self._shopify_stock_status[url] = is_available

            # Filter out non-coffee products using base class logic (a defensive
            # net that, e.g., also excludes the workshop classes via their name).
            if self.is_coffee_product_url(url) and self.is_coffee_product_name(product.get("title", "")):
                found_urls.append(url)

        # Dedup on the canonical/formatted URLs (post-preprocess) so the returned
        # list is unique even before the base discover_all_product_urls dedups.
        return self.deduplicate_urls(found_urls)
