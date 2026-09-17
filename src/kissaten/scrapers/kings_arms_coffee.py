"""Kings Arms Coffee scraper implementation with Shopify JSON extraction."""

import logging

from . import _curl_http as httpx
from .base import WebBotAuth
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)

# country=US pins the US home market so the full catalogue is returned in USD.
_MARKET_PARAM = "country=US"


@register_scraper(
    name="kings-arms-coffee",
    display_name="Kings Arms Coffee",
    roaster_name="Kings Arms Coffee",
    website="https://kingsarmscoffee.com",
    description="Tampa, Florida roaster and café offering single origins, co-fermented "
    "Colombian lots and house blends (Bayshore, Skyway Espresso)",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class KingsArmsCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Kings Arms Coffee (kingsarmscoffee.com) using Shopify products.json.

    The brand styles itself "Kings Arms" (no apostrophe) — keep that verbatim.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Kings Arms Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Kings Arms Coffee",
            base_url="https://kingsarmscoffee.com",
            products_json_urls=["https://kingsarmscoffee.com/collections/coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The curated `coffee` collection still contains the online gift card;
        # subscriptions (African/Latin/Brew Club) and merch live in other
        # collections and never enter this URL set.
        self.exclude_slugs = [
            "gift-card",
            "gift",
        ]

        # Pin the home-market currency: /cart.js confirms the store serves
        # USD, so make it authoritative against Shopify Markets geolocation.
        self.store_currency = "USD"
        self._currency_detected = True

        # kingsarmscoffee.com's edge intermittently rejects curl_cffi's
        # default libcurl TLS fingerprint (403 on products.json), while the
        # "chrome" impersonation profile negotiates successfully. Rebuild the
        # client with that profile, preserving headers/auth/proxy (twoday.py
        # pattern).
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
        non-US egress IP are market-filtered and the returned catalogue is
        incomplete (limited co-ferment lots are hidden).
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
        """Standardize Kings Arms Coffee product URLs.

        The canonical product pages are the no-collection form
        ``/products/<handle>``, so strip the ``/collections/<slug>`` segment.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
