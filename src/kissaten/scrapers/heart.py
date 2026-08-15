"""Heart Coffee Roasters scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)

_COLLECTION_SEGMENT = "/collections/beans"
# curl_cffi requests are geo/market-detected as the UK (GB) by heartroasters.com,
# which serves a reduced catalog (missing several coffees) priced in GBP. Passing
# country=US pins the US market so the full coffee catalog is returned in USD.
_MARKET_PARAM = "country=US"


@register_scraper(
    name="heart",
    display_name="Heart",
    roaster_name="Heart",
    website="https://www.heartroasters.com",
    description="Specialty coffee roaster founded in Portland, Oregon, known for "
    "transparent sourcing with published FOB costs and a focus on single origin coffees.",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="available",
)
class HeartScraper(ShopifyJsonScraper):
    """Scraper for Heart Coffee Roasters (heartroasters.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Heart Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Heart",
            base_url="https://www.heartroasters.com",
            products_json_urls=["https://www.heartroasters.com/collections/beans/products.json"],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Heart's storefront geolocates curl_cffi requests to the UK (GBP) unless the
        # US market is pinned via country=US (see _fetch_all_shopify_products). Force the
        # currency to USD and mark it as detected so the collection-page detection path
        # in _scrape_new_products (which would see the GBP market) is skipped.
        self.store_currency = "USD"
        self._currency_detected = True

        # Exclude non-coffee products that appear in the beans collection
        # (sample packs, subscriptions) plus common non-coffee categories.
        self.exclude_slugs = [
            "sample",
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "clothing",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def _fetch_all_shopify_products(self, products_json_url: str) -> list[dict]:
        """Fetch all products from the products.json endpoint with US market pinned.

        Mirrors ``ShopifyJsonScraper._fetch_all_shopify_products`` but appends
        ``country=US`` to each paginated request. Without it, curl_cffi requests are
        geo/market-detected as the UK and the returned catalog is incomplete (missing
        several coffees) and priced in GBP.
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
        """Strip the collection segment to match Heart's canonical product URLs.

        ShopifyJsonScraper builds product URLs as
        ``<products.json base>/products/<handle>``, which yields a
        ``/collections/beans/products/<handle>`` form. Heart's real product
        pages are served at ``/products/<handle>`` (querying the ``/products/``
        form directly returns 200), so normalize the URL to that form.
        """
        url = url.replace(_COLLECTION_SEGMENT, "")
        return url
