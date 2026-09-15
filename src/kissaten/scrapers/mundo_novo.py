"""Mundo Novo Coffee scraper implementation with Shopify JSON extraction."""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="mundo-novo",
    display_name="Mundo Novo Coffee",
    roaster_name="Mundo Novo Coffee",
    website="https://mundonovocoffee.com",
    description="Madrid-based specialty coffee roaster sourcing Latin American "
    "single origins, home of the James Hoffmann Fermentation Project pack.",
    requires_api_key=True,
    currency="EUR",
    country="Spain",
    status="experimental",
)
class MundoNovoScraper(ShopifyJsonScraper):
    """Scraper for Mundo Novo Coffee (mundonovocoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Mundo Novo Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Mundo Novo Coffee",
            base_url="https://mundonovocoffee.com",
            products_json_urls=["https://mundonovocoffee.com/collections/cafe/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=1.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The curated "Café" collection only contains bean products; keep a
        # defensive exclude list for subscription/equipment leaks.
        self.exclude_slugs = [
            "suscripcion",
            "gift-card",
            "regalo",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Strip the collection segment to match Mundo Novo's canonical product URLs.

        ShopifyJsonScraper builds product URLs as
        ``<products.json base>/products/<handle>``, which yields a
        ``/collections/cafe/products/<handle>`` form. Mundo Novo's canonical
        product pages are served at ``/products/<handle>``.
        """
        return re.sub(r"/collections/[^/]+/products/", "/products/", url)
