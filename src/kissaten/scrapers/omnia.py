"""Omnia Coffee Roasters scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)

# curl_cffi requests from a datacenter IP are geo/market-detected by Shopify
# Markets and served converted prices (e.g. GBP for a UK IP, USD for a US
# one). Passing country=CA pins Omnia's home market so products.json always
# reports CAD prices.
_MARKET_PARAM = "country=CA"


@register_scraper(
    name="omnia",
    display_name="Omnia Coffee Roasters",
    roaster_name="Omnia Coffee Roasters",
    website="https://www.omniacoffeeroasters.com",
    description="Micro-roastery roasting specialty coffee beans in Toronto, Canada, "
    "with seasonal micro-lot single origins.",
    requires_api_key=True,
    currency="CAD",
    country="Canada",
    status="available",
)
class OmniaCoffeeRoastersScraper(ShopifyJsonScraper):
    """Scraper for Omnia Coffee Roasters (omniacoffeeroasters.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Omnia Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Omnia Coffee Roasters",
            base_url="https://www.omniacoffeeroasters.com",
            products_json_urls=["https://www.omniacoffeeroasters.com/collections/frontpage/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Home market is pinned via country=CA (see _fetch_all_shopify_products).
        # Force the currency to CAD and mark it as detected so the
        # collection-page detection path in _scrape_new_products (which could
        # see a geo-converted currency) is skipped.
        self.store_currency = "CAD"
        self._currency_detected = True

        # Exclude non-coffee products that appear in the frontpage collection
        # (subscription packs) plus common non-coffee categories.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "barista",
            "class",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def _fetch_all_shopify_products(self, products_json_url: str) -> list[dict]:
        """Fetch all products from the products.json endpoint with the CA market pinned.

        Mirrors ``ShopifyJsonScraper._fetch_all_shopify_products`` but appends
        ``country=CA`` to each paginated request. Without it, Shopify Markets
        geo-detects the datacenter IP and serves converted prices (GBP/USD/…)
        instead of Omnia's home CAD prices.
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
        """Strip the collection segment to match Omnia's canonical product URLs.

        ShopifyJsonScraper builds product URLs as
        ``<products.json base>/products/<handle>``, which yields a
        ``/collections/frontpage/products/<handle>`` form. Omnia's canonical
        product pages are served at ``/products/<handle>`` (the pages declare
        that form in their <link rel="canonical"> tag).
        """
        return url.replace("/collections/frontpage", "")
