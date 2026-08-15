"""HEX Coffee Roasters scraper implementation with Shopify JSON extraction."""

import logging

from bs4 import BeautifulSoup

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="hex",
    display_name="HEX",
    roaster_name="Hex",
    website="https://hex.coffee",
    description="Specialty coffee roaster based in Charlotte, North Carolina, "
    "focused on experimental and single-origin coffees sourced from "
    "producer partners around the world.",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="available",
)
class HexCoffeeScraper(ShopifyJsonScraper):
    """Scraper for HEX Coffee Roasters (hex.coffee) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize the HEX Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Hex",
            base_url="https://hex.coffee",
            products_json_urls=[
                "https://hex.coffee/collections/cofefve/products.json",
            ],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
            custom_headers={"Accept-Language": ""},
        )

        # The cofefve collection is already coffee-only, but keep defensive
        # excludes for any non-coffee items that may appear later.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merch",
            "apparel",
            "mug",
            "tumbler",
            "hoodie",
            "tshirt",
            "t-shirt",
            "beanie",
            "cap",
            "cold-brew",
            "keg",
            "instant",
            "burrito",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize HEX Coffee product URLs.

        HEX's canonical product pages live at ``/products/<handle>`` without a
        collection segment, so strip the ``/collections/cofefve`` prefix that
        ``ShopifyJsonScraper`` builds from the products.json URL base.
        """
        url = url.replace("/collections/cofefve/products/", "/products/")
        return url

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Limit extraction to the product documentation section.

        The ``div.coffee-product__documentation`` block contains both the
        farmer/process context (``.coffee-product__context``) and the structured
        technical spec (``dl.coffee-product__technical``: farm, region,
        varieties, elevation, processing) that the Shopify JSON body_html lacks.
        Pruning to it keeps AI token usage low while retaining all bean detail.
        """
        doc = soup.select_one("div.coffee-product__documentation")
        if doc:
            logger.debug("Limiting extraction to div.coffee-product__documentation")
            return doc
        return soup
