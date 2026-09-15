"""Steel Oak Coffee scraper implementation with Shopify JSON extraction."""

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
    name="steel-oak-coffee",
    display_name="Steel Oak Coffee",
    roaster_name="Steel Oak Coffee",
    website="https://steeloakcoffee.com",
    description="Ormond Beach, Florida specialty coffee roaster offering "
    "single origins and blends, including the James Hoffmann / Lucia Solis "
    "Fermentation Project.",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class SteelOakCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Steel Oak Coffee (steeloakcoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Steel Oak Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Steel Oak Coffee",
            base_url="https://steeloakcoffee.com",
            products_json_urls=["https://steeloakcoffee.com/collections/coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Steel Oak's storefront converts prices to EUR for clients sending an
        # Accept-Language header (including the scraper's default en-US one).
        # The home market is pinned via country=US (see
        # _fetch_all_shopify_products); force the currency to USD and mark it
        # as detected so the collection-page detection path in
        # _scrape_new_products (which would see the EUR market) is skipped.
        self.store_currency = "USD"
        self._currency_detected = True

        # The curated coffee collection holds beans plus subscription products
        # (explorer-gift-subscription); the Fermentation Project coffee is
        # kept and flagged downstream.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
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

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Steel Oak Coffee product URLs.

        Steel Oak's canonical product pages are the no-collection form
        ``/products/<handle>``, so strip the ``/collections/<slug>`` segment.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
