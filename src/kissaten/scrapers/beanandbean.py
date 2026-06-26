"""Bean & Bean Coffee Roasters scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="bean-and-bean",
    display_name="Bean & Bean Coffee Roasters",
    roaster_name="Bean & Bean Coffee Roasters",
    website="https://beannbeancoffee.com",
    description="Female-founded NYC specialty coffee roaster known for sourcing competition-grade "
    "single-origin coffees from women-led farms worldwide",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="available",
)
class BeanAndBeanScraper(ShopifyJsonScraper):
    """Scraper for Bean & Bean Coffee Roasters (beannbeancoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Bean & Bean Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Bean & Bean Coffee Roasters",
            base_url="https://beannbeancoffee.com",
            products_json_urls=[
                "https://beannbeancoffee.com/collections/shop-all-coffee/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "tumbler",
            "gift-box",
            "mug",
            "tee",
            "shirt",
            "apparel",
            "downtown",  # No origin details
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Normalize Bean & Bean product URLs to /products/{handle}.

        The shop-all-coffee products.json produces URLs like
        ``/collections/shop-all-coffee/products/{handle}``. We strip the
        collection prefix so the canonical URL is ``/products/{handle}``.

        Args:
            url: Product URL produced by the base scraper

        Returns:
            Canonical product URL at ``/products/{handle}``
        """
        if "/products/" not in url:
            return url

        handle = url.split("/products/")[-1].rstrip("/")
        return f"{self.base_url}/products/{handle}"
