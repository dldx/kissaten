"""Bell Lane Coffee scraper implementation with Shopify JSON extraction."""

import logging

from bs4 import BeautifulSoup, Tag

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="bell-lane",
    display_name="Bell Lane",
    roaster_name="Bell Lane",
    website="https://www.belllane.ie",
    description="B Corp certified specialty coffee roastery based in Mullingar, Ireland with a focus on long-term relationship and positive impact.",
    requires_api_key=True,
    currency="EUR",
    country="Republic of Ireland",
    status="available",
)
class BellLaneScraper(ShopifyJsonScraper):
    """Scraper for Bell Lane (belllane.ie) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Bell Lane scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Bell Lane",
            base_url="https://www.belllane.ie",
            products_json_urls=["https://www.belllane.ie/collections/coffee/products.json"],
            scrape_product_pages=True,
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
            "apparel",
            "mug",
            "tumbler",
            "hoodie",
            "tshirt",
            "capsules",
            "pods",
            "cold-brew-cans",
            "easy-pour",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Strip the /collections/coffee segment to match canonical product URLs.

        ShopifyJsonScraper builds URLs from the products.json base, inserting
        /collections/coffee. Canonical Bell Lane product URLs are
        https://www.belllane.ie/products/<handle>.
        """
        return url.replace("/collections/coffee/products/", "/products/")

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup | Tag:
        """Limit extraction to the product info block for efficiency.

        Args:
            soup: Original BeautifulSoup object of the product page.

        Returns:
            The ``div.product-info__block-list`` subtree, or the full soup if
            the selector is not found.
        """
        block = soup.select_one("div.product-info__block-list")
        if block:
            logger.debug("Limiting extraction to div.product-info__block-list")
            return block
        return soup
