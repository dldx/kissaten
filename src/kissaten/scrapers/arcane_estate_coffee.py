"""Arcane Estate Coffee scraper implementation with Shopify JSON extraction."""

import logging

from . import _curl_http as httpx
from .base import WebBotAuth
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="arcane-estate-coffee",
    display_name="Arcane Estate",
    roaster_name="Arcane Estate",
    website="https://arcaneestatecoffee.com",
    description="NYC café at 37 Cornelia St specialising in Panamanian estate coffees "
    "(La Reina, Villa Luna) from Boquete and Tierras Altas producers",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class ArcaneEstateCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Arcane Estate Coffee (arcaneestatecoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Arcane Estate Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Arcane Estate",
            base_url="https://arcaneestatecoffee.com",
            products_json_urls=["https://arcaneestatecoffee.com/collections/all/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The store is a small café catalogue: coffee bags plus a monthly
        # subscription. Exclude the subscription and any gift card.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
        ]

        # Pin the home-market currency: individual product JSON reports
        # ``price_currency: "USD"`` and /cart.js confirms the store serves
        # USD, so make it authoritative against Shopify Markets geolocation.
        self.store_currency = "USD"
        self._currency_detected = True

        # arcaneestatecoffee.com's edge rejects curl_cffi's default libcurl
        # TLS fingerprint (403 on products.json), while the "chrome"
        # impersonation profile negotiates successfully. Rebuild the client
        # with that profile, preserving headers/auth/proxy (twoday.py pattern).
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
        """Standardize Arcane Estate product URLs.

        The canonical product pages are the no-collection form
        ``/products/<handle>``, so strip the ``/collections/<slug>`` segment.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
