"""Rosslyn Coffee scraper implementation with Shopify JSON extraction.

Rosslyn Coffee (rosslyncoffee.com) is a London café chain on Shopify. Its
site nav curates a dedicated ``coffee-for-home`` collection that captures
exactly the whole-bean coffees (currently four: roasted for milk / black /
filter, plus the Financial Times 'Daily Scoop' special-edition single
origin). The remaining catalogue items (ceramic mugs, coffee vouchers, gift
subscriptions) live in separate collections and are never part of the
``coffee-for-home`` payload.

The Shopify ``body_html`` for each coffee carries the bean details the
``CoffeeBean`` schema needs (flavour notes, origin, brewing methods), so the
cheapest JSON-only path is used: ``scrape_product_pages=False`` with
``use_optimized_mode=True`` and no page caching. The rendered product page
adds nothing the JSON lacks.

Canonical URLs are the no-collection form ``/products/<handle>`` (confirmed
via a live redirect), so the collection segment built from the products.json
base is stripped in ``preprocess_product_url``.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="rosslyn",
    display_name="Rosslyn Coffee",
    roaster_name="Rosslyn Coffee",
    website="https://www.rosslyncoffee.com",
    description="London café chain roasting a curated line of whole-bean "
    "coffees for milk, black and filter brewing, plus a Financial Times "
    "special-edition single origin. A small, genuinely thin catalogue.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class RosslynScraper(ShopifyJsonScraper):
    """Scraper for Rosslyn Coffee (rosslyncoffee.com) using Shopify products.json.

    Uses the curated ``coffee-for-home`` collection, which mirrors the
    roaster's own nav for whole-bean coffee, rather than
    ``collections/all`` (which also mixes in mugs, vouchers and gift
    subscriptions).
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Rosslyn Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Rosslyn Coffee",
            base_url="https://www.rosslyncoffee.com",
            products_json_urls=[
                "https://www.rosslyncoffee.com/collections/coffee-for-home/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Rosslyn is a UK store priced in GBP. The storefront can geolocate the
        # datacenter IP to a non-GBP market, so pin the home currency and mark
        # it as detected to skip the collection-page currency-detection path.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Exclude genuine non-coffee products only. Do NOT exclude sampler /
        # taster-pack slugs here: the base class flags tasting kits
        # (flag-don't-exclude) so they land in the admin review queue rather
        # than being dropped. The coffees in ``coffee-for-home`` carry no
        # `product_type`, so the slug list is the primary net for any
        # non-coffee that might surface.
        self.exclude_slugs = [
            "subscription",
            "gift-subscription",
            "gift-card",
            "giftcard",
            "voucher",
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
            "capsules",
            "pods",
            "cold-brew-cans",
            "easy-pour",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Rosslyn Coffee product URLs.

        The live site redirects product pages to the no-collection form
        ``/products/<handle>``, so strip the ``/collections/<slug>`` segment
        that each products.json base URL injects.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs, keeping only whole-bean coffee.

        The default base-class filter (``is_coffee_product_url`` +
        ``is_coffee_product_name``) is intentionally conservative and would
        pass mugs/vouchers that don't trip an exclude keyword. Because Rosslyn
        leaves ``product_type`` empty for every product, we cannot whitelist
        ``product_type == "Coffee"``; instead we drop products whose
        ``product_type`` is a known non-coffee category as a defensive net on
        top of ``exclude_slugs``. The curated ``coffee-for-home`` collection
        already yields only the four whole-bean coffees.
        """
        non_coffee_types = {
            "mug",
            "gift card",
            "gift voucher",
            "voucher",
            "subscription",
            "equipment",
            "merchandise",
            "apparel",
            "accessory",
        }

        products = await self._fetch_all_shopify_products(store_url)
        found_urls = []

        for product in products:
            handle = product.get("handle")
            if not handle:
                continue

            product_type = (product.get("product_type") or "").strip().lower()
            if product_type in non_coffee_types:
                logger.debug(f"Skipping non-coffee product type: {handle} ({product_type})")
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

        # Dedup on the canonical/formatted URLs (post-preprocess) so the
        # returned list is unique even before the base discover_all_product_urls
        # dedups.
        return self.deduplicate_urls(found_urls)
