"""Quarter Horse Coffee scraper implementation with Shopify JSON extraction.

Quarter Horse Coffee (quarterhorsecoffee.com) is a Birmingham, UK specialty
coffee roaster on Shopify. Its site nav curates the roasted-bean catalogue into
a single ``beans`` collection, which this scraper consumes:

* ``collections/beans/products.json`` — the store's own whole-bean collection.
  It is curated to coffee (verified 2026-08: 15 published products, all either
  Coffee-typed whole beans or curated sampler/selection packs), so unlike
  ``collections/all`` (130 mixed products) it needs no aggressive category
  filtering. The handful of ``Wholesale``/``Gift Cards``/``Merch``/equipment
  types that exist in ``all`` never appear here, and the wholesale ``-ws`` /
  ``-wholesale`` duplicate handles are deliberately out of scope because this
  collection already lists the retail (canonical) form of each bean.

The Shopify ``body_html`` carries the bean details the ``CoffeeBean`` schema
needs (tasting notes, origin, producer, process), so the cheapest JSON-only
path is used: ``scrape_product_pages=False`` with ``use_optimized_mode=True``
and no page caching. The rendered product page adds nothing the JSON lacks.

Canonical URLs are the no-collection form ``/products/<handle>``, so the
``/collections/beans`` segment built from the products.json base is stripped in
``preprocess_product_url``.

Curated sampler/selection packs (the Coffee Club ``explore-pack``, the 6-bag
``coffee-samples-gift-set-pack``, and the ``mixed-package`` Roaster's Selection)
are whole-coffee samplers: they are kept (not excluded) and flagged as tasting
kits so they land in the admin review queue instead of public search.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)

# Shopify product_type values that clearly are not whole-bean coffee. The beans
# collection is curated, so these are belt-and-braces; they keep any accidental
# wholesale/merch/gift/equipment row that sneaks into the feed from reaching
# extraction without needing an exhaustive handle list.
_NON_COFFEE_PRODUCT_TYPES = frozenset(
    {
        "Wholesale",
        "Wholesale Template",
        "Gift Cards",
        "Merch",
        "Ancillary",
        "Store Stock",
    }
)


@register_scraper(
    name="quarter-horse",
    display_name="Quarter Horse Coffee",
    roaster_name="Quarter Horse Coffee",
    website="https://www.quarterhorsecoffee.com",
    description="Birmingham specialty coffee roaster and espresso bar offering "
    "single origin filter coffees, espresso blends and seasonal offerings, "
    "roasted in-house with an emphasis on accessible everyday speciality coffee.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class QuarterHorseScraper(ShopifyJsonScraper):
    """Scraper for Quarter Horse Coffee (quarterhorsecoffee.com) using Shopify products.json.

    Uses the curated ``beans`` collection rather than ``collections/all``, which
    also mixes in wholesale lots, subscriptions, gift cards, equipment and merch.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Quarter Horse Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Quarter Horse Coffee",
            base_url="https://www.quarterhorsecoffee.com",
            products_json_urls=[
                "https://www.quarterhorsecoffee.com/collections/beans/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Quarter Horse is a UK store priced in GBP. The storefront can
        # geolocate the datacenter IP to a non-GBP market, so pin the home
        # currency and mark it as detected to skip the collection-page
        # currency-detection path.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Exclude genuine non-coffee products only. Do NOT exclude sampler /
        # taster-pack / selection slugs here: the base class flags tasting kits
        # (flag-don't-exclude) so they land in the admin review queue rather
        # than being dropped. Note "gift-card" / "giftcard" (not a bare "gift")
        # so the "Coffee Samples Gift Set" handle is not caught.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "giftcard",
            "wholesale",
            "-ws",
            "equipment",
            "brewing",
            "grinder",
            "v60",
            "chemex",
            "aeropress",
            "kalita",
            "hario",
            "filter-paper",
            "filter-papers",
            "merch",
            "merchandise",
            "apparel",
            "mug",
            "tumbler",
            "hoodie",
            "tshirt",
            "capsules",
            "pods",
            "cold-brew-cans",
            "easy-pour",
            "tea",
            "course",
            "masterclass",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Quarter Horse product URLs.

        The live site canonicalizes product pages to the no-collection form
        ``/products/<handle>`` (the products.json base injects a
        ``/collections/beans`` segment), so strip it to align with the site's
        real canonical URLs.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract whole-bean product URLs from the beans collection.

        The curated ``beans`` collection already holds only whole beans and
        coffee sampler packs, so the main job is to drop any product whose
        Shopify ``product_type`` marks it as clearly not whole-bean coffee
        (wholesale lots, gift cards, merch, equipment rows) while keeping the
        Coffee-typed beans and the sampler/selection packs (which are later
        flagged as tasting kits, not excluded). The base-class
        ``is_coffee_product_url`` / ``is_coffee_product_name`` checks then
        serve as a final conservative guard.
        """
        products = await self._fetch_all_shopify_products(store_url)
        found_urls = []

        for product in products:
            handle = product.get("handle")
            if not handle:
                continue

            product_type = (product.get("product_type") or "").strip()
            if product_type in _NON_COFFEE_PRODUCT_TYPES:
                logger.debug(
                    f"Skipping non-coffee product type '{product_type}': {handle}"
                )
                continue

            # Skip explicitly excluded product slugs (matches if slug is a substring of handle).
            if any(slug in handle for slug in self.exclude_slugs):
                logger.debug(f"Skipping excluded product slug: {handle}")
                continue

            # Build product URL using the base of the products.json URL.
            base_path = store_url.replace("/products.json", "")
            url = f"{base_path}/products/{handle}"

            # Preprocess the URL (e.g. to remove collection segments).
            url = self.preprocess_product_url(url)

            # Store metadata for later enrichment and stock status.
            self._shopify_product_data[url] = product

            # A product is in stock if any of its variants are available.
            is_available = any(v.get("available", False) for v in product.get("variants", []))
            self._shopify_stock_status[url] = is_available

            # Filter out non-coffee products using base class logic.
            if self.is_coffee_product_url(url) and self.is_coffee_product_name(product.get("title", "")):
                found_urls.append(url)

        # Dedup on the canonical/formatted URLs (post-preprocess) so a product
        # surfacing in multiple collections counts once.
        return self.deduplicate_urls(found_urls)

    def postprocess_review_flags(self, bean, url: str):
        """Flag curated multi-bag samplers/selection packs as tasting kits.

        The base tasting-kit URL/name patterns catch some of these (the
        ``coffee-samples-gift-set-pack`` handle carries "sample"), but the two
        remaining curated packs need an explicit flag so they go through the
        admin review queue instead of public search:

        * ``explore-pack`` — the Explore Pack sampler for the Coffee Club.
        * ``mixed-package`` — the Roaster's Selection, four seasonal whole-bean
          bags.
        """
        if bean is not None and any(
            token in str(url) for token in ("explore-pack", "mixed-package")
        ):
            bean.is_tasting_kit = True
        return bean
