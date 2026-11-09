"""Mame Coffee scraper implementation (Shopify storefront).

MAME Roastery (mame.coffee) migrated off a legacy WooCommerce theme to a
Shopify storefront (verified live 2026-11: ``/product-category/*`` URLs 301 to
``/collections/*`` and the homepage serves ``shopify.exit_interstitial`` JS).

The coffee catalogue lives at ``https://mame.coffee/products.json`` (single
page, well under the 250-product limit). Products are tagged ``Daily``,
``Competition``, ``Equipment`` and ``Subscription``; equipment and
subscription handles are excluded so only coffee beans are scraped.

HTTP: the Shopify edge 403s curl_cffi's default libcurl TLS fingerprint while
the "chrome" impersonation profile negotiates successfully (verified live:
plain fingerprint → 403 on every products.json request; ``impersonate="chrome"``
→ 200), so the client is rebuilt with that profile (same pattern as
``oddy_knocky.py`` / ``twoday.py``).
"""

import logging

from ..ai import CoffeeDataExtractor
from . import _curl_http as httpx
from .base import WebBotAuth
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="mame-coffee",
    display_name="Mame Coffee",
    roaster_name="MAME Roastery",
    website="https://mame.coffee",
    description="Swiss specialty coffee roaster offering daily coffee and competition-grade beans",
    requires_api_key=True,
    currency="CHF",
    country="Switzerland",
    status="available",
)
class MameCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Mame Coffee (mame.coffee) using Shopify products.json.

    The store publishes its full catalogue (daily + competition coffees,
    equipment, subscriptions) through a single ``/products.json`` feed;
    non-coffee handles are excluded by slug and the home currency is pinned
    to CHF.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Mame Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="MAME Roastery",
            base_url="https://mame.coffee",
            products_json_urls=[
                "https://mame.coffee/products.json",
            ],
            scrape_product_pages=True,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

        # mame.coffee's Shopify edge rejects curl_cffi's default libcurl TLS
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

        # Mame is a Swiss store priced in CHF. Pin the home currency and mark
        # it as detected so the collection-page currency-detection path can
        # never overwrite it with a geo-located market price.
        self.store_currency = "CHF"
        self._currency_detected = True

        # Non-coffee handles published in the products.json feed:
        #   equipment: hario-v60-paper-filter, hario-v60-01-02,
        #              hario-glass-server, aeropress, ankomn-container,
        #              mame-x-hario-switch-purion-02
        #   subscriptions: coffee-subscription, competition-subscription
        # Substring matching (slug in handle) covers all of them.
        self.exclude_slugs = [
            "hario",
            "aeropress",
            "ankomn",
            "subscription",
        ]
