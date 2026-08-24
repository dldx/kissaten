"""Artisan Coffee scraper implementation with Shopify JSON extraction.

Artisan Coffee (artisancoffee.co.uk, Edinburgh) sources its beans from
Curious Roo Coffee Roasters (curiousroo.com), a London Shopify roaster;
their online store is the Curious Roo Shopify store. The curated
``coffee`` collection on curiousroo.com contains exactly the currently
available whole-bean coffees plus two subscription entries, so filtering
out subscriptions/gifts within it yields only beans.

Canonical product URLs are the no-collection form ``/products/<handle>``
(confirmed via the page's ``rel=canonical``), so the collection segment the
products.json base would inject is stripped in ``preprocess_product_url``.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="artisan",
    display_name="Artisan Coffee",
    roaster_name="Artisan Coffee",
    website="https://www.artisancoffee.co.uk",
    description="Artisan Coffee (Edinburgh) sources its coffee from Curious Roo "
    "Coffee Roasters, a London specialty roaster; the beans are sold through "
    "the Curious Roo Shopify store (curiousroo.com).",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class ArtisanScraper(ShopifyJsonScraper):
    """Scraper for Artisan Coffee's beans (sold at curiousroo.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Artisan scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Artisan Coffee",
            base_url="https://curiousroo.com",
            products_json_urls=[
                "https://curiousroo.com/collections/coffee/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Exclude non-coffee products that appear in the curated coffee
        # collection (subscriptions / gifting / merch).
        self.exclude_slugs = [
            "subscription",
            "gift",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

        # The store serves a geolocated presentment currency to datacenter IPs;
        # the roaster is UK-based and priced in GBP.
        self.store_currency = "GBP"
        self._currency_detected = True

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Curious Roo product URLs.

        Curious Roo's canonical/live product pages are the no-collection form
        ``/products/<handle>``, so strip the ``/collections/coffee`` segment
        that the products.json base URL injects.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs, keeping only coffees from the curated collection.

        The curated ``coffee`` collection mixes beans with two subscription /
        gift entries; exclude those via ``exclude_slugs`` and let the base
        coffee-name filters drop anything else.
        """
        products = await self._fetch_all_shopify_products(store_url)
        found_urls = []

        for product in products:
            handle = product.get("handle")
            if not handle:
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

        # Dedup on the canonical/formatted URLs (post-preprocess).
        return self.deduplicate_urls(found_urls)

    def _extract_currency_from_html(self, soup) -> str:
        """Pin the store currency to GBP.

        Curious Roo serves a geo-localized presentment currency in its
        ``Shopify.currency`` script and ``og:price:currency`` meta; force GBP
        so the AI prices the beans in the roaster's home currency.
        """
        return "GBP"

    def postprocess_extracted_bean(self, bean):
        """Force the bean currency to GBP (store base currency)."""
        bean = super().postprocess_extracted_bean(bean)
        bean.currency = "GBP"
        return bean
