"""Ómra Coffee scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)

# curl_cffi requests from a datacenter IP are geo/market-detected by Shopify
# Markets and served converted prices (EUR was observed for a EU IP). Passing
# country=GB pins Ómra's home market so products.json always reports GBP
# prices.
_MARKET_PARAM = "country=GB"


@register_scraper(
    name="omra-coffee",
    display_name="Ómra Coffee",
    roaster_name="Ómra Coffee",
    website="https://omra.coffee",
    description="Specialty coffee roastery in Derry roasting seasonal editions, "
    "home of the James Hoffmann Fermentation Project Coffee Tasting Set.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="experimental",
)
class OmraCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Ómra Coffee (omra.coffee) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Ómra Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Ómra Coffee",
            base_url="https://omra.coffee",
            products_json_urls=["https://omra.coffee/collections/coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=1.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Home market is pinned via country=GB (see _fetch_all_shopify_products).
        # Force the currency to GBP and mark it as detected so the
        # collection-page detection path in _scrape_new_products (which could
        # see a geo-converted currency) is skipped.
        self.store_currency = "GBP"
        self._currency_detected = True

        # The curated "Specialty Coffee" collection only contains coffee
        # products; keep a defensive exclude list.
        self.exclude_slugs = [
            "gift-card",
            "subscription",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def _fetch_all_shopify_products(self, products_json_url: str) -> list[dict]:
        """Fetch all products from the products.json endpoint with the GB market pinned.

        Mirrors ``ShopifyJsonScraper._fetch_all_shopify_products`` but appends
        ``country=GB`` to each paginated request. Without it, Shopify Markets
        geo-detects the datacenter IP and serves converted prices (EUR was
        observed) instead of Ómra's home GBP prices.
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
        """Strip the collection segment to match Ómra's canonical product URLs.

        ShopifyJsonScraper builds product URLs as
        ``<products.json base>/products/<handle>``, which yields a
        ``/collections/coffee/products/<handle>`` form. Ómra's canonical
        product pages are served at ``/products/<handle>``.
        """
        return re.sub(r"/collections/[^/]+/products/", "/products/", url)
