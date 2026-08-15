"""Code Black Coffee scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="code-black",
    display_name="Code Black Coffee",
    roaster_name="Code Black",
    website="https://codeblackcoffee.com.au",
    description="Melbourne-based Australian specialty coffee roaster (3056) known for single "
    "origin coffees, house blends and low-caffeine shifts, roasted at Code Black Roastery.",
    requires_api_key=True,
    currency="AUD",
    country="Australia",
    status="available",
)
class CodeBlackCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Code Black Coffee (codeblackcoffee.com.au) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Code Black Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Code Black",
            base_url="https://codeblackcoffee.com.au",
            products_json_urls=[
                "https://codeblackcoffee.com.au/collections/coffee/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Exclude non-bag products (subscriptions and multi-bean bundles).
        # The dedicated /collections/coffee collection already excludes
        # equipment and merch, so this only needs to trim bundles/subscriptions.
        self.exclude_slugs = [
            "subscription",
            "bundle",
            "gift",
            "wholesale",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Code Black product URLs to the canonical no-collection form.

        The site's real/canonical product pages are served at ``/products/<handle>``
        (the collection segment is not part of a product's canonical URL). The
        products.json base derives ``/collections/coffee/products/<handle>``, so we
        strip the collection segment to match the canonical form.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1]
            return f"{self.base_url}/products/{handle}"
        return url
