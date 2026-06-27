"""Kaffa Roastery scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="kaffa",
    display_name="Kaffa Roastery",
    roaster_name="Kaffa",
    website="https://kaffaroastery.fi",
    description="Finnish specialty coffee roaster based in Helsinki. Kaffa has a strong focus on transparency and sustainability.",
    requires_api_key=True,
    currency="EUR",
    country="Finland",
    status="available",
)
class KaffaScraper(ShopifyJsonScraper):
    """Scraper for Kaffa Roastery (kaffaroastery.fi) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Kaffa scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Kaffa",
            base_url="https://kaffaroastery.fi",
            products_json_urls=[
                "https://kaffaroastery.fi/en/collections/kahvit/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude non-coffee products (subscriptions, gift cards, equipment, etc.)
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "sampler",
            "taster-pack",
            "apparel",
            "mug",
            "tumbler",
            "hoodie",
            "tshirt",
            "capsules",
            "pods",
            "cold-brew-cans",
            "easy-pour",
            "cascara"
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Kaffa product URLs to /en/products/<handle>.

        Shopify builds product URLs under each collection path; we strip the
        collection segment so all products share a single canonical URL.
        """
        if "/collections/" in url and "/products/" in url:
            handle = url.split("/products/", 1)[1]
            return f"{self.base_url}/en/products/{handle}"
        return url
