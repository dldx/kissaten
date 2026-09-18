"""Bean's Beans scraper implementation with Shopify JSON extraction."""

import logging

from . import _curl_http as httpx
from .base import WebBotAuth
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="beans-beans",
    display_name="Bean's Beans",
    roaster_name="Bean's Beans",
    website="https://beansbeans.coffee",
    description="Online-only micro-roaster selling small, frequently sold-out lots of "
    "rare single-origin coffees (Gesha Village, La Papaya, Airworks exclusives)",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class BeansBeansScraper(ShopifyJsonScraper):
    """Scraper for Bean's Beans (beansbeans.coffee) using Shopify products.json.

    Not to be confused with Bean & Bean (``bean-and-bean``), a different NYC roaster.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Bean's Beans scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Bean's Beans",
            base_url="https://beansbeans.coffee",
            products_json_urls=["https://beansbeans.coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The catalogue is coffee-only (no collections, no equipment/merch);
        # most lots are sold out at any given time, which is expected.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
        ]

        # Pin the home-market currency: /cart.js confirms the store serves
        # USD, so make it authoritative against Shopify Markets geolocation.
        self.store_currency = "USD"
        self._currency_detected = True

        # beansbeans.coffee intermittently rejects curl_cffi's default
        # libcurl TLS fingerprint; the "chrome" impersonation profile is
        # reliably accepted. Rebuild the client with that profile, preserving
        # headers/auth/proxy (twoday.py pattern).
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

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Bean's Beans product URLs.

        The canonical product pages are the no-collection form
        ``/products/<handle>``, so strip any collection segment.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
