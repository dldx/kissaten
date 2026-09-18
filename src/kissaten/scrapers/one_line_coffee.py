"""One Line Coffee scraper implementation with Shopify JSON extraction.

JSON-only scraping: the products.json ``body_html`` already carries the
tasting notes, blend composition, and process details the AI needs, and the
product pages add nothing beyond it, so we skip page fetching entirely.
"""

import logging

from . import _curl_http as httpx
from .base import WebBotAuth
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)

# country=US pins the US home market so the full catalogue is returned in USD
# (the store market-filters/converts for non-US egress IPs).
_MARKET_PARAM = "country=US"


@register_scraper(
    name="one-line-coffee",
    display_name="One Line Coffee",
    roaster_name="One Line Coffee",
    website="https://www.onelinecoffee.com",
    description="Columbus, Ohio roaster and cafés offering seasonal single origins, "
    "espresso blends (Method, Process, Technique), decafs and cold brew",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class OneLineCoffeeScraper(ShopifyJsonScraper):
    """Scraper for One Line Coffee (onelinecoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize One Line Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="One Line Coffee",
            base_url="https://www.onelinecoffee.com",
            products_json_urls=["https://www.onelinecoffee.com/collections/coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The curated `coffee` collection covers all beans (including limited
        # releases); tea, equipment, merch, subscriptions and gift bundles live
        # in their own collections and never enter this URL set.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift-bundle",
        ]

        # Pin the home-market currency: /cart.js confirms the store serves
        # USD, so make it authoritative against Shopify Markets geolocation.
        self.store_currency = "USD"
        self._currency_detected = True

        # onelinecoffee.com's edge rejects curl_cffi's default libcurl TLS
        # fingerprint (403 on products.json), while the "chrome" impersonation
        # profile negotiates successfully. Rebuild the client with that
        # profile, preserving headers/auth/proxy (twoday.py pattern).
        proxy_url = self.https_proxy or self.http_proxy
        client_kwargs: dict = {
            "headers": self.headers,
            "timeout": self.timeout,
            "auth": WebBotAuth(self),
            "impersonate": "chrome",
        }
        if proxy_url:
            client_kwargs["proxy"] = proxy_url
        self.client = httpx.AsyncClient(**client_kwargs)

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def _fetch_all_shopify_products(self, products_json_url: str) -> list[dict]:
        """Fetch all products from the products.json endpoint with US market pinned.

        Mirrors ``ShopifyJsonScraper._fetch_all_shopify_products`` but appends
        ``country=US`` to each paginated request. Without it, requests from a
        non-US egress IP are market-filtered (the collection can come back
        empty) and priced in GBP instead of USD.
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
        """Standardize One Line Coffee product URLs.

        The canonical product pages are the no-collection form
        ``/products/<handle>``, so strip the ``/collections/<slug>`` segment.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
