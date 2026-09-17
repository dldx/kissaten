"""Merit Coffee scraper implementation with Shopify JSON extraction."""

import logging

from bs4 import BeautifulSoup

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="merit-coffee",
    display_name="Merit",
    roaster_name="Merit",
    website="https://meritcoffee.com",
    description="Texas-based specialty roaster (San Antonio and Houston) offering seasonal "
    "single origins, espresso blends and a diner-inspired café programme.",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class MeritCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Merit Coffee (meritcoffee.com) using Shopify products.json.

    Page extraction is required: the product pages carry a collapsed
    ``Coffee Specs`` accordion (origin, producer, process, cultivar, altitude)
    and a ``Roast Level`` accordion that the products.json ``body_html`` does
    not include. ``preprocess_product_soup`` prunes each page to the
    ``rte-formatter`` description blocks and ``accordion-custom`` sections so
    the AI sees only bean-relevant content.

    Uses the curated ``coffee`` collection, which contains only bean products;
    merch, tea, gear and subscriptions live in other collections (a
    ``subscription`` slug guard is kept as a safety net).
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Merit Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Merit",
            base_url="https://meritcoffee.com",
            products_json_urls=[
                "https://meritcoffee.com/collections/coffee/products.json",
            ],
            scrape_product_pages=True,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        self.exclude_slugs = [
            "subscription",
        ]

        # Pin the home-market currency (verified against /cart.js): Shopify
        # Markets may serve geo-converted prices to datacenter IPs.
        self.store_currency = "USD"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Merit product URLs.

        Merit's canonical product pages are the no-collection form
        ``/products/<handle>``, so strip the ``/collections/<slug>`` segment.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Prune the product page to descriptions and detail accordions.

        Merit (Shopify "Ride" theme) renders the tasting-note description as
        ``rte-formatter`` blocks and the Coffee Specs / Roast Level details as
        ``accordion-custom`` elements. We build a new minimal soup WITH a
        body: ShopifyJsonScraper injects the Shopify JSON context
        (name/price/variants) at the top of ``soup.body`` AFTER this hook
        returns, so keeping a valid body preserves that data.
        """
        keepers = soup.select("rte-formatter, accordion-custom")
        if not keepers:
            return soup

        minimal = BeautifulSoup("<html><head></head><body></body></html>", "html.parser")
        for keeper in keepers:
            minimal.body.append(keeper)
        return minimal
