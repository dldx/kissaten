"""Apricity Coffee scraper implementation with Shopify JSON extraction."""

import logging

from bs4 import BeautifulSoup

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="apricity",
    display_name="Apricity",
    roaster_name="Apricity",
    website="https://apricitycoffee.co.uk",
    description="Independent UK specialty coffee roaster sourcing exceptional single "
    "origin coffees with transparency and care",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class ApricityCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Apricity (apricitycoffee.co.uk) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Apricity Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Apricity",
            base_url="https://apricitycoffee.co.uk",
            products_json_urls=["https://apricitycoffee.co.uk/collections/all-coffees/products.json"],
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
            # Apricity-specific non-coffee / wholesale handles
            "3kg",  # wholesale 3kg bags (aji-orange-3kg, silk-choc-3kg, ...)
            "timemore",  # Crystal Eye brewer + Crystal Eye filter papers
            "v60",  # Hario V60 dripper + V60 filter papers
            "atmos",  # Fellow Atmos airtight canister
            "tee",  # long-sleeve-tee
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Apricity URLs by removing collection segments."""
        if "/collections/" in url and "/products/" in url:
            # e.g. https://apricitycoffee.co.uk/collections/all-coffees/products/slug
            #   -> https://apricitycoffee.co.uk/products/slug
            try:
                handle = url.split("/products/")[-1].split("?")[0]
                return f"{self.base_url}/products/{handle}"
            except Exception:
                return url
        return url

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Filter the product page HTML down to the bean detail accordions.

        Apricity hides origin/process/variety/tasting notes/story behind
        collapsible ``div.product__accordion`` sections, so we keep only those
        to give the AI the bean information without extraneous page chrome.

        We build a new minimal soup WITH a body: ShopifyJsonScraper injects the
        Shopify JSON context (name/price/variants) at the top of ``soup.body``
        AFTER this hook returns, so keeping a valid body preserves that data.
        """
        accordions = soup.select("div.product__accordion")
        if not accordions:
            return soup

        minimal = BeautifulSoup("<html><head></head><body></body></html>", "html.parser")
        for accordion in accordions:
            minimal.body.append(accordion)
        return minimal
