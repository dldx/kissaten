"""Flying Horse Coffee scraper implementation with Shopify JSON extraction.

Flying Horse Coffee (flyinghorsecoffee.com) is a UK-based specialty coffee
roaster. The store is Shopify-hosted; the curated ``coffee`` collection is the
site's coffee shop page and contains exactly the currently-available whole-bean
coffees (espresso blend, espresso single origin, filter single origin and the
decaf), all classified ``product_type == "Coffee"``.

The broader ``beans`` collection mixes those four beans with brewing gear and
capsules (All Day Brewing Capsules, Opal One Capsule Machine, Huskee Cup, V60
filter papers, AeroPress, Filtropa filters), so we filter the curated ``coffee``
collection to ``product_type == "Coffee"`` only, plus an ``exclude_slugs``
defensive net, to keep just the beans.

Product URLs are canonicalised to the no-collection form used by the live site
(``/products/<handle>``, confirmed via the page's ``rel=canonical``). The Shopify
JSON ``body_html`` carries the bean detail (origin, process, tasting notes), so
the scraper runs in JSON-only mode (no product-page HTML sent to the AI).

Currency is pinned to GBP (the store serves GBP prices) to guard against
Shopify Markets geo-detection converting prices for the scraper's datacenter IP.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="flying-horse",
    display_name="Flying Horse",
    roaster_name="Flying Horse",
    website="https://flyinghorsecoffee.com",
    description="UK-based specialty coffee roaster offering an espresso blend, "
    "espresso and filter single origins, and a caffeine-free option, sourced "
    "from producers globally",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class FlyingHorseScraper(ShopifyJsonScraper):
    """Scraper for Flying Horse Coffee (flyinghorsecoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Flying Horse Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Flying Horse",
            base_url="https://flyinghorsecoffee.com",
            products_json_urls=[
                "https://flyinghorsecoffee.com/collections/coffee/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The curated `coffee` collection is already filtered to beans, but keep
        # an exclude list as a defensive net in case the collection later mixes
        # in brewing gear / capsules (the `beans` collection does).
        self.exclude_slugs = [
            "subscription",
            "gift-card",
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
            "capsules",
            "pods",
            "machine",
            "huskee",
            "v60",
            "filtropa",
            "aeropress",
        ]

        # Pin GBP so Shopify Markets geo-detection can't convert prices for the
        # scraper's datacenter IP (the store's home market is the UK).
        self.store_currency = "GBP"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Flying Horse Coffee product URLs.

        Flying Horse's canonical/live product pages are the no-collection form
        ``/products/<handle>`` (confirmed via the page's ``rel=canonical``), so
        strip the ``/collections/<slug>`` segment that the products.json base
        URL injects.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs, keeping only whole-bean coffee.

        The base-class filter (``is_coffee_product_url`` +
        ``is_coffee_product_name``) is intentionally conservative; the ``beans``
        collection mixes beans with brewing gear whose handles may not trip an
        exclude keyword. Filter explicitly on the Shopify
        ``product_type == "Coffee"`` before building the URL, then apply the
        exclude-slug net as a second line of defence.
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

        # Dedup on the canonical/formatted URLs (post-preprocess) so the returned
        # list is unique even before the base discover_all_product_urls dedups.
        return self.deduplicate_urls(found_urls)
