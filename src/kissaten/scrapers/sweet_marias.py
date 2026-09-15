"""Sweet Maria's scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="sweet-marias",
    display_name="Sweet Maria's",
    roaster_name="Sweet Maria's",
    website="https://www.sweetmarias.com",
    description="Oakland, California home-roasting institution; this scraper covers only their "
    "roasted-coffee range — the green (unroasted) coffee catalogue is intentionally not scraped",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class SweetMariasScraper(ShopifyJsonScraper):
    """Scraper for Sweet Maria's (sweetmarias.com) using Shopify products.json.

    Sweet Maria's is primarily a green (unroasted) coffee seller; Kissaten does
    not track green beans, so this scraper intentionally targets only the
    ``roasted-coffee`` collection (their roasted 'Next Roast' range and
    subscription). Roasting equipment, merch and the green-coffee catalogue
    live in other collections and are not fetched.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Sweet Maria's scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Sweet Maria's",
            base_url="https://www.sweetmarias.com",
            products_json_urls=[
                "https://www.sweetmarias.com/collections/roasted-coffee/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The roasted-coffee subscription is a service, not a bean — exclude it.
        self.exclude_slugs = [
            "rstd-subs",
        ]

        # Pin the home-market currency: Shopify Markets may serve
        # geo-converted prices to datacenter IPs, and the base-class
        # display-name currency lookup falls back to GBP. The home
        # currency was verified against /cart.js, so make it authoritative.
        self.store_currency = "USD"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Sweet Maria's product URLs.

        Sweet Maria's canonical product pages are the no-collection form
        ``/products/<handle>``; stripping the collection segment also dedups
        blends that appear in both collections.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
