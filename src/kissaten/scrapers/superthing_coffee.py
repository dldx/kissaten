"""Superthing Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="superthing-coffee",
    display_name="Superthing",
    roaster_name="Superthing",
    website="https://superthingcoffee.com",
    description="Austin, Texas micro-roaster offering espresso-forward blends and single "
    "origins (many experimental Colombian anaerobic and co-ferment lots) in 10oz, 2lb and "
    "5lb bags",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class SuperthingCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Superthing Coffee (superthingcoffee.com) using Shopify products.json.

    The curated ``/collections/coffees`` products.json carries all the bean
    detail (components, process, farm story with altitudes, tasting notes) in
    its ``body_html``, so no product-page scraping is needed.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Superthing Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Superthing",
            base_url="https://superthingcoffee.com",
            products_json_urls=["https://superthingcoffee.com/collections/coffees/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The coffees collection is already coffee-only; exclude
        # subscription products defensively (substring matches
        # `*-subscription` handles).
        self.exclude_slugs = [
            "subscription",
        ]

        # Pin the home-market currency: verified against /cart.js (USD), so
        # Shopify Markets geo-conversion cannot override it.
        self.store_currency = "USD"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Superthing product URLs.

        Superthing's canonical product pages are the no-collection form
        ``/products/<handle>``, so strip the ``/collections/<slug>`` segment.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
