"""Pollards Coffee scraper implementation with Shopify JSON extraction.

Pollards Coffee (pollardscoffee.co.uk) is a Sheffield roaster with a retail
shop at 627 Ecclesall Road plus a wholesale/roastery operation. The curated
``/collections/all-coffees`` collection is a clean whole-bean list (product
type "Freshly Roasted Coffee") whose products.json ``body_html`` already
carries the full description and whose variants carry weight/price, so we
scrape JSON-only. The storefront's edge rejects curl_cffi's default libcurl
fingerprint with HTTP 403, so the client is rebuilt with the ``"chrome"``
impersonation profile (same pattern as ``twoday.py``).
"""

import logging

from ..ai import CoffeeDataExtractor
from . import _curl_http as httpx
from .base import WebBotAuth
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="pollards",
    display_name="Pollards Coffee",
    roaster_name="Pollards Coffee",
    website="https://pollardscoffee.co.uk",
    description="Sheffield coffee roaster with a retail shop at 627 Ecclesall Road "
    "plus a wholesale/roastery operation, offering freshly roasted whole-bean coffees.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class PollardsScraper(ShopifyJsonScraper):
    """Scraper for Pollards Coffee (pollardscoffee.co.uk) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Pollards Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Pollards Coffee",
            base_url="https://pollardscoffee.co.uk",
            products_json_urls=[
                "https://pollardscoffee.co.uk/collections/all-coffees/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Pin the store currency to GBP. The base-class currency detection
        # would otherwise be skipped anyway since we scrape JSON-only, but
        # pinning guarantees a geo-localized storefront can never convert
        # prices away from the roaster's home market.
        self.store_currency = "GBP"
        self._currency_detected = True

        # pollardscoffee.co.uk's edge rejects curl_cffi's default libcurl TLS
        # fingerprint (HTTP 403 on every request), while the "chrome"
        # impersonation profile negotiates successfully. Rebuild the client
        # with that profile, preserving headers/auth/proxy.
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

        # The curated all-coffees collection is whole-bean only, but keep a
        # safety net for equipment/services. Curated sampler/taster kits are
        # deliberately NOT excluded — they are flagged is_tasting_kit and land
        # in the admin review queue instead of being dropped.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "apparel",
            "mug",
            "tumbler",
            "hoodie",
            "tshirt",
            "grinder",
            "v60",
            "kettle",
            "scale",
            "capsules",
            "pods",
            "cold-brew-cans",
            "easy-pour",
        ]

        if api_key:
            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Pollards product URLs to the canonical form.

        The store serves product pages at ``/products/<handle>`` (no collection
        segment). The base class builds collection-prefixed URLs from the
        products.json base, so strip the collection segment to match the site's
        real canonical URLs.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1]
            return f"{self.base_url}/products/{handle}"
        return url
