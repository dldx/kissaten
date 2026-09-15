"""Roasted Brown scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="roasted-brown",
    display_name="Roasted Brown",
    roaster_name="Roasted Brown",
    website="https://www.roastedbrown.com",
    description="Dublin-based Irish micro-roaster offering seasonal single-origin espresso "
    "and filter coffees, including the Fermentation Project cupping kit",
    requires_api_key=True,
    currency="EUR",
    country="Republic of Ireland",
    status="experimental",
)
class RoastedBrownScraper(ShopifyJsonScraper):
    """Scraper for Roasted Brown (roastedbrown.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Roasted Brown scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Roasted Brown",
            base_url="https://www.roastedbrown.com",
            products_json_urls=["https://www.roastedbrown.com/collections/all-coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The curated `all-coffee` collection keeps the Guatemala Fermentation
        # Project coffee; the cupping spoon/bowls bundled into the same
        # collection are accessories, not coffee. Note: exclude slugs must be
        # specific ("cupping-spoon"/"cupping-bowl") because the Fermentation
        # Project handle itself contains "cupping".
        self.exclude_slugs = [
            "cupping-spoon",
            "cupping-bowl",
        ]

        # Pin the home-market currency: Shopify Markets may serve
        # geo-converted prices to datacenter IPs, and the base-class
        # display-name currency lookup falls back to GBP. The home
        # currency was verified against /cart.js, so make it authoritative.
        self.store_currency = "EUR"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def is_coffee_product_url(self, url: str, required_path_patterns: list[str] | None = None) -> bool:
        """Keep the Fermentation Project coffee despite the base-class filter.

        The base URL filter excludes the generic ``cupping`` pattern, but the
        Fermentation Project handle is
        ``guatemala-the-fermentation-project-for-cupping-filter-brewing`` —
        it is a coffee, not a cupping accessory. Whitelist it and defer to the
        base filter for everything else.
        """
        if "the-fermentation-project" in url:
            return True
        return super().is_coffee_product_url(url, required_path_patterns)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Roasted Brown product URLs.

        Roasted Brown's canonical product pages are the no-collection form
        ``/products/<handle>``, so strip the ``/collections/<slug>`` segment.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
