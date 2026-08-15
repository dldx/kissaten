"""Single O scraper implementation with Shopify JSON extraction.

Single O is a specialty coffee roaster and cafe based in Sydney, Australia
(since 2003). Products are served via Shopify's products.json endpoint from
the ``coffee`` collection, which is curated to beans (single origins,
blends and decaf) plus a handful of drip-bag "parachute" products that are
excluded here.
"""

import logging

from bs4 import BeautifulSoup

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="single-o",
    display_name="Single O",
    roaster_name="Single O",
    website="https://singleo.com.au",
    description="Sydney-based specialty coffee roaster and cafe since 2003, "
    "known for structured single origin coffees and signature blends like "
    "Reservoir and Killerbee.",
    requires_api_key=True,
    currency="AUD",
    country="Australia",
    status="available",
)
class SingleOScraper(ShopifyJsonScraper):
    """Scraper for Single O (singleo.com.au) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Single O scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Single O",
            base_url="https://singleo.com.au",
            products_json_urls=["https://singleo.com.au/collections/coffee/products.json"],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Single O is an Australian roaster priced in AUD: the products.json
        # variant prices and the reliable (clean-UA) pages all serve AUD. The
        # bot-facing requests can be geo/locale-served a GBP-marked page, which
        # would otherwise mislabel the bean currency. Pin the store currency to
        # AUD up front and treat it as already-detected so later page parsing
        # does not overwrite it; ShopifyJsonScraper.postprocess_extracted_bean
        # then stamps AUD onto every extracted bean.
        self.store_currency = "AUD"
        self._currency_detected = True

        # Drop non-bean products: drip-bag "parachute" products (flight bags)
        # and the Filter Show subscription, plus generic non-coffee fallbacks.
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
            "t-shirt",
            "tee",
            "hoodie",
            "capsules",
            "pods",
            "cold-brew-cans",
            "parachute",
            "multichutes",
            "filter-show",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Single O product URLs.

        ShopifyJsonScraper builds URLs under the collection path
        (``/collections/coffee/products/...``) but Single O's canonical
        product pages are the no-collection form ``/products/<handle>``.
        Strip the collection segment to match the site's real URLs.
        """
        return url.replace("/collections/coffee/products/", "/products/")

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Limit extraction to the product details section for efficiency.

        ``div.c-product-main__details`` holds the structured info items
        (Taste, Process, Variety, Altitude, Region, Producer), the origin
        synopsis and the brew-method table. The Shopify product JSON
        (description / body_html, variants, price) is injected separately,
        so pruning to this small section keeps AI token usage low.
        """
        details = soup.select_one("div.c-product-main__details")
        if details:
            logger.debug("Limiting extraction to div.c-product-main__details")
            return details
        return soup
