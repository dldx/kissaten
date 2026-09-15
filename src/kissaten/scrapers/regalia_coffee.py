"""Regalia Coffee scraper implementation with Shopify JSON extraction."""

import logging
from typing import Any

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)

# With the scraper's default ``Accept-Language: en-US`` header, Shopify Markets
# serves EUR-converted prices (the store has a EUR market for EU customers).
# Passing country=US pins the home market so products.json reports USD prices.
_MARKET_PARAM = "country=US"


@register_scraper(
    name="regalia-coffee",
    display_name="Regalia",
    roaster_name="Regalia",
    website="https://regaliacoffee.com",
    description="Miami-based specialty coffee roaster focused on rare Colombian "
    "and Ethiopian single origins, including design-fermented lots.",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class RegaliaCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Regalia (regaliacoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Regalia scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Regalia",
            base_url="https://regaliacoffee.com",
            products_json_urls=["https://regaliacoffee.com/collections/all/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Regalia's storefront converts prices to EUR for clients sending an
        # Accept-Language header (including the scraper's default en-US one).
        # The home market is pinned via country=US (see
        # _fetch_all_shopify_products); force the currency to USD and mark it
        # as detected so the collection-page detection path in
        # _scrape_new_products (which would see the EUR market) is skipped.
        self.store_currency = "USD"
        self._currency_detected = True

        # collections/all mixes coffee with grinders, brew gear, books, apparel,
        # gift cards and subscriptions, so _extract_product_urls_from_store
        # filters on product_type == "Coffee". Keep a small exclude list as a
        # safety net against future non-coffee products typed as "Coffee".
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def _fetch_all_shopify_products(self, products_json_url: str) -> list[dict[str, Any]]:
        """Fetch all products from the products.json endpoint with the US market pinned.

        Mirrors ``ShopifyJsonScraper._fetch_all_shopify_products`` but appends
        ``country=US`` to each paginated request. Without it, requests sending
        an ``Accept-Language`` header (the scraper's client sends en-US) receive
        EUR-converted prices from Shopify Markets.
        """
        all_products = []
        page = 1
        limit = 250

        while True:
            url = f"{products_json_url}?{_MARKET_PARAM}&limit={limit}&page={page}"
            logger.info(f"Fetching Shopify products: {url}")

            data, use_playwright = await self._fetch_page_with_escalation(url)
            if data is None:
                if products_json_url not in self._failed_listing_urls:
                    self._failed_listing_urls.append(products_json_url)
                break

            products = data.get("products", [])
            if not products:
                break

            all_products.extend(products)
            logger.debug(f"Fetched {len(products)} products from page {page}")

            if len(products) < limit:
                break

            page += 1
            if use_playwright:
                logger.debug(f"Page {page - 1} escalated to Playwright; re-attempting httpx on page {page}.")

        return all_products

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs, keeping only whole-bean coffee.

        ``collections/all`` mixes many non-coffee categories (grinders, brew
        gear, books, apparel, gift cards, subscriptions), so filter explicitly
        on the Shopify ``product_type == "Coffee"`` before building the URL.
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

        return found_urls

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Regalia product URLs.

        Regalia's canonical product pages are the no-collection form
        ``/products/<handle>``, so strip any ``/collections/<slug>`` segment.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
