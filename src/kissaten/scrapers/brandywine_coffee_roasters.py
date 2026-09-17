"""Brandywine Coffee Roasters scraper implementation with Shopify JSON extraction.

JSON-only scraping: the products.json ``body_html`` already carries the
tasting notes, process, and producer details the AI needs, so we skip page
fetching entirely.
"""

import logging

from . import _curl_http as httpx
from .base import WebBotAuth
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="brandywine-coffee-roasters",
    display_name="Brandywine",
    roaster_name="Brandywine",
    website="https://www.brandywinecoffeeroasters.com",
    description="Wilmington, Delaware roaster known for playful, creative coffees "
    "(co-ferments, themed blends, Galactic Standard instants) alongside classic single origins",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class BrandywineCoffeeRoastersScraper(ShopifyJsonScraper):
    """Scraper for Brandywine (brandywinecoffeeroasters.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Brandywine scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Brandywine",
            base_url="https://www.brandywinecoffeeroasters.com",
            products_json_urls=[
                "https://www.brandywinecoffeeroasters.com/collections/coffee/products.json",
                # Catches the odd coffee (e.g. tropical gesha) that never makes
                # it into the `coffee` collection; gift-card overlap is deduped.
                "https://www.brandywinecoffeeroasters.com/collections/all-coffee-1/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The `coffee` collection also carries merch (crewnecks, mugs, spoon
        # rests); herbal teas are dropped by tag. Tea lives in its own
        # collection which we never fetch.
        self.exclude_slugs = [
            "gift-card",
            "gift",
            "crewneck",
            "mug",
            "spoon-rest",
            "shirt",
            "tumbler",
            "water-bottle",
            "shot-glass",
            "beach-towel",
            "toy",
        ]

        # Pin the home-market currency: /cart.js confirms the store serves
        # USD, so make it authoritative against Shopify Markets geolocation.
        self.store_currency = "USD"
        self._currency_detected = True

        # brandywinecoffeeroasters.com's edge rejects curl_cffi's default
        # libcurl TLS fingerprint (403 / empty products.json), while the
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

    def _get_tasting_kit_url_patterns(self) -> list[str]:
        """Add Brandywine's club products to the tasting-kit patterns.

        The annual "Thank Goodness It's Spooky Coffee Club" is a one-off
        curated bundle (a month of coffees plus a shirt), not a perpetual
        subscription, so it is extracted and flagged for admin review instead
        of excluded.
        """
        return super()._get_tasting_kit_url_patterns() + ["coffee-club"]

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract coffee URLs, dropping tagged tea products.

        Some collections mix herbal teas in with a ``Tea`` tag; exclude those
        here so they never reach the coffee pipeline.
        """
        found_urls = await super()._extract_product_urls_from_store(store_url)

        kept_urls = []
        for url in found_urls:
            product = self._shopify_product_data.get(url, {})
            tags = [str(t).strip().lower() for t in product.get("tags", [])]
            if any(tag == "tea" or tag.endswith(" tea") for tag in tags):
                logger.debug(f"Skipping tagged tea product: {product.get('handle')}")
                self._shopify_product_data.pop(url, None)
                self._shopify_stock_status.pop(url, None)
                continue
            kept_urls.append(url)
        return kept_urls

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Brandywine product URLs.

        The canonical product pages are the no-collection form
        ``/products/<handle>`` (the collection pages link to the
        collection-prefixed form but set ``/products/<handle>`` as canonical),
        so strip the ``/collections/<slug>`` segment. This also deduplicates
        products that appear in both fetched collections.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
