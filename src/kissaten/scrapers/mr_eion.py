"""Mr Eion scraper implementation with Shopify JSON extraction.

Mr Eion Coffee Roaster (mreion.com) is an Edinburgh, Scotland roaster on a
Shopify storefront. The store is a mixed merchant: the root ``products.json``
carries 27 products but only 13 are ``product_type == "Coffee"`` — the rest
are tea & infusions, coffee filters, makers/machines, merch, an Aeropress,
gift cards and Hario gear.

Route: the curated ``coffee`` collection advertises ~49 products (mixing in
subscriptions, blends and regional overlaps) while ghost collections exist
("Coffee - House Blends", "Myanmar", "New Products" all return 0), so instead
of trusting collection metadata the whole catalogue is fetched from the root
``products.json`` and filtered down to ``product_type == "Coffee"``. That
yields the 12 real whole-bean coffees (the 13th Coffee-typed product is
``ongoing-subscription-roasters-choice``, a subscription, excluded by slug).

Shape: the Shopify JSON ``body_html`` carries the description and tasting
notes, and the rendered product page shows the same content (no structured
origin/farm/process/variety block, no cupping score). So the scraper runs
JSON-only (``scrape_product_pages=False``, ``use_optimized_mode=True``),
feeding the injected Shopify JSON context straight to the AI — no per-page
HTML fetch, which is the cheapest option.

Currency is pinned to GBP (verified ``Shopify.currency`` active GBP on the
live payload) and ``_currency_detected`` is set in ``__init__`` so no
geo-detected market conversion can override it.

Canonical product URLs are the no-collection ``/products/<handle>`` form,
which the root products.json base URL already produces; ``preprocess_product_url``
defensively strips any collection segment anyway.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="mr-eion",
    display_name="Mr Eion",
    roaster_name="Mr Eion",
    website="https://mreion.com",
    description="Edinburgh speciality coffee roaster, small-batch roasting of single "
    "origins and house blends in Scotland. Mixed Shopify merchant (also sells tea, "
    "filters and equipment) — scraper keeps only whole-bean coffee.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class MrEionScraper(ShopifyJsonScraper):
    """Scraper for Mr Eion Coffee Roaster (mreion.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Mr Eion scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Mr Eion",
            base_url="https://mreion.com",
            products_json_urls=["https://mreion.com/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Exclude genuine non-coffee products. The product_type == "Coffee"
        # filter in _extract_product_urls_from_store already drops tea,
        # equipment, merch, gift cards and makers; this catches the one
        # Coffee-typed non-bean (the ongoing roaster's-choice subscription).
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "apparel",
            "mug",
            "tumbler",
            "hoodie",
            "tshirt",
            "capsules",
            "pods",
            "filters",
            "aeropress",
            "hario",
            "chemex",
            "v60",
        ]

        # Store serves GBP natively; pin defensively (geo-detected currency
        # must never override the home-market GBP prices).
        self.store_currency = "GBP"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Mr Eion product URLs to the canonical form.

        Mr Eion's canonical/live product pages are the no-collection form
        ``/products/<handle>`` (verified live; returns HTTP 200). The root
        products.json base URL already yields that form; this is a defensive
        normalization in case a collection URL ever appears.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs, keeping only whole-bean coffee.

        The root products.json mixes 13 ``Coffee``-typed items (the real beans)
        with tea, equipment, merch, gift cards and makers. Filter explicitly on
        the Shopify ``product_type == "Coffee"`` before building URLs so non-
        coffee product types never reach the bean pipeline, then apply the
        exclude_slugs (which catches the roaster's-choice subscription that is
        itself typed ``Coffee``).
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
