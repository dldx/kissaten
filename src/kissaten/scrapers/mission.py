"""Mission Coffee Works scraper implementation with Shopify JSON extraction.

Mission Coffee Works (missioncoffeeworks.com) is a London-based specialty
coffee roaster and importer. The Shopify store is a UK store priced in GBP.

There is no clean curated coffee collection: the site's ``coffee`` ("All
Coffee") collection is 79 products, inflated by a subscription-variant
explosion — Pivot, Uphill, Roaster's Choice Filter and Bells each appear as
separate 12-month / 6-month / 3-month subscription products alongside the
single whole-bean base product. Equipment, merch, tea and gift cards fill
out the rest of the catalogue.

So this scraper uses the global ``products.json`` endpoint and filters on the
Shopify ``product_type == "Coffee"`` (captures the 27 coffee-classed
products). Subscriptions are themselves Coffee-classed products, so they are
NOT caught by that filter; they are excluded instead by handle:

* ``coffee-subscription-*`` products (ongoing / fixed-term) carry an empty
  ``body_html`` and are matched by the ``subscription`` exclude slug.
* The term-variant dups (``*-12-months`` / ``*-6-months`` / ``*-3-months``)
  are matched by the ``-12-months`` / ``-6-months`` / ``-3-months`` exclude
  slugs, which leave the base beans (``pivot-espresso``, ``up-hill-espresso``,
  ``bells-espresso``, ``seasonal-filter-blend``) in place.

After filtering and exclusion, 11 whole-bean coffee products remain. The
``body_html`` on these is rich (origin country/region, producer/farm, process,
variety, altitude and tasting notes), so the scraper runs JSON-only
(``scrape_product_pages=False``) with ``use_optimized_mode=True`` — the
cheapest path. No product-page scraping means no carousel/accordion concern.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="mission",
    display_name="Mission Coffee Works",
    roaster_name="Mission Coffee Works",
    website="https://www.missioncoffeeworks.com/",
    description="London-based specialty coffee roaster and importer, sourcing "
    "direct micro-lot coffees from around the world and roasting them ethically "
    "in the UK.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class MissionScraper(ShopifyJsonScraper):
    """Scraper for Mission Coffee Works (missioncoffeeworks.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Mission Coffee Works scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Mission Coffee Works",
            base_url="https://www.missioncoffeeworks.com",
            products_json_urls=["https://www.missioncoffeeworks.com/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=1.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Exclude non-coffee products and subscription-variant duplicates.
        # ``subscription`` catches the coffee-subscription-* services;
        # ``-12-months`` / ``-6-months`` / ``-3-months`` catch the term-variant
        # subscription products while leaving the single base beans intact.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "giftcard",
            "gift",
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
            "tea",
            "matcha",
            "kettle",
            "grinder",
            "v60",
            "aeropress",
            "hario",
            "timemore",
            "fellow",
            "comandante",
            "moccamaster",
            "filtropa",
            "filters",
            "paper",
            "decanter",
            "keepcup",
            "dripper",
            "cafetiere",
            "brewer",
            "scale",
            "mizudashi",
            "french-press",
            "cleaner",
            "sack",
            "hot-chocolate",
            "chocolate",
            "-12-months",
            "-6-months",
            "-3-months",
        ]

        # Pin the store currency to GBP. Mission is a UK roaster priced in GBP
        # (the products.json prices are GBP), but Shopify Markets may serve a
        # geo-localized presentment currency to the scraper's datacenter IP.
        # Pinning prevents a converted currency (e.g. USD) from being stamped
        # onto every bean.
        self.store_currency = "GBP"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

        # Remove the Accept-Language header so Shopify serves the base GBP
        # market instead of a geo-localized presentment currency. Any
        # Accept-Language (even en-GB) can trigger conversion for this store.
        self.headers.pop("Accept-Language", None)
        self.client._base_headers.pop("Accept-Language", None)
        session_headers = getattr(self.client._session, "headers", None)
        if session_headers:
            session_headers.pop("Accept-Language", None)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Mission product URLs.

        The global ``products.json`` already yields the canonical
        no-collection form (``/products/<handle>``) that the live site serves,
        but strip any ``/collections/<name>/`` segment defensively in case the
        endpoint changes to a collection-scoped URL.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs, keeping only whole-bean coffee.

        The curated ``coffee`` collection is inflated by subscription variants,
        so instead filter the global ``products.json`` on the Shopify
        ``product_type == "Coffee"`` and then drop the subscription products by
        handle via ``exclude_slugs``.
        """
        products = await self._fetch_all_shopify_products(store_url)
        found_urls = []

        for product in products:
            handle = product.get("handle")
            if not handle:
                continue

            # Only accept products Shopify itself classifies as coffee.
            if product.get("product_type", "") != "Coffee":
                logger.debug(f"Skipping non-coffee product type: {handle} ({product.get('product_type')})")
                continue

            # Skip subscription products / equipment and the term-variant dups.
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

        # Dedup on the canonical/formatted URLs (post-preprocess) so the returned
        # list is unique even before the base discover_all_product_urls dedups.
        return self.deduplicate_urls(found_urls)
