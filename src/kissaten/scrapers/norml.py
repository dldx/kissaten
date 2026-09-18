"""Norml (norml coffee ppl) scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="norml",
    display_name="Norml",
    roaster_name="Norml",
    website="https://normlppl.coffee",
    description="Micro-roaster 'norml coffee ppl' roasting a single rotating blend weekly in "
    "tiny batches, alongside a green-coffee programme for home roasters (green lots excluded "
    "here — only the roasted blend is tracked).",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class NormlScraper(ShopifyJsonScraper):
    """Scraper for Norml (normlppl.coffee) using Shopify products.json.

    JSON-only extraction: the products.json ``body_html`` carries tasting
    notes and (for the roasted blend) roast schedule details.

    There is no curated roasted-coffee collection, so ``collections/all`` is
    fetched and filtered. Green (unroasted) coffee lots are excluded, following
    the roaster-scraper precedent (``conscious_coffees.py``, ``coopers_coffee.py``):
    the Kissaten database tracks roasted coffee, so only the weekly rotating
    blend is eligible. Subscriptions and the brew-gear filter papers are
    excluded as well.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Norml scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Norml",
            base_url="https://normlppl.coffee",
            products_json_urls=[
                "https://normlppl.coffee/collections/all/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        self.exclude_slugs = [
            "subscription",
            "green-coffee",
            "filter-paper",
        ]

        # Pin the home-market currency (verified against /cart.js): Shopify
        # Markets may serve geo-converted prices to datacenter IPs.
        self.store_currency = "USD"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Norml product URLs.

        Norml's canonical product pages are the no-collection form
        ``/products/<handle>``, so strip the ``/collections/<slug>`` segment.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
