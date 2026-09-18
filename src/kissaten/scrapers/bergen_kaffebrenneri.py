"""Kaffe Brenneri (Bergen Kaffebrenneri) scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="bergen-kaffebrenneri",
    display_name="Kaffe Brenneri",
    roaster_name="Kaffe Brenneri",
    website="https://bergenkaffebrenneri.no",
    description="Bergen-based Norwegian specialty coffee roaster offering single origins, blends "
    "and subscription boxes, plus the Fermentation Project tasting kit",
    requires_api_key=True,
    currency="NOK",
    country="Norway",
    status="experimental",
)
class BergenKaffebrenneriScraper(ShopifyJsonScraper):
    """Scraper for Kaffe Brenneri (bergenkaffebrenneri.no) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Kaffe Brenneri scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Kaffe Brenneri",
            base_url="https://bergenkaffebrenneri.no",
            products_json_urls=["https://bergenkaffebrenneri.no/collections/all/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Pin the home-market currency: Shopify Markets can serve geo-converted
        # prices depending on caller IP / Accept-Language, so runtime detection
        # is not trusted.
        self.store_currency = "NOK"
        self._currency_detected = True

        # The Kaffebønner tag view is not exposed as a products.json endpoint,
        # so scrape collections/all and exclude the Norwegian non-coffee items:
        # subscriptions (abonnement), courses (kurs), gift cards (gavekort),
        # cups (kopp), filters, machines, merch (caps/beanie/towel/flask),
        # the anniversary book (jubileumsbok) and a DVD film.
        self.exclude_slugs = [
            "abonnement",
            "manedens-bkb",
            "kurs",
            "gavekort",
            "kopp",
            "filter",
            "la-marzocco",
            "lommelerke",
            "handkle",
            "luer",
            "caps",
            "dvd",
            "jubileumsbok",
            "gift-card",
            "gift",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def _canonicalize_url(self, url: str) -> str:
        # Canonical product pages are /products/<handle> (collection-prefixed
        # URLs 301-redirect there).
        return re.sub(r"/collections/[^/]+/products/", "/products/", url)

    def preprocess_product_url(self, url: str) -> str:
        """Canonicalize collection-prefixed product URLs to ``/products/<handle>``."""
        return self._canonicalize_url(url)
