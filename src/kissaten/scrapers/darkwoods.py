"""Darkwoods Coffee scraper implementation with Shopify JSON extraction."""

import logging

from bs4 import BeautifulSoup

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="darkwoods",
    display_name="Darkwoods Coffee",
    roaster_name="Darkwoods",
    website="https://darkwoodscoffee.co.uk",
    description="UK specialty coffee roaster in the Yorkshire Dales known for carefully "
    "sourced single origin coffees and award-winning blends",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class DarkwoodsScraper(ShopifyJsonScraper):
    """Scraper for Darkwoods Coffee (darkwoodscoffee.co.uk) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Darkwoods Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Darkwoods",
            base_url="https://darkwoodscoffee.co.uk",
            products_json_urls=["https://darkwoodscoffee.co.uk/collections/coffee/products.json"],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude non-coffee products (gift cards, gift tins, chocolate, sample boxes, equipment)
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift-tins",
            "chocolate",
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

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Filter the product page HTML down to the bean detail accordions.

        Darkwoods hides origin/process/variety/altitude/roast and the producer
        story behind collapsible ``div.product__accordion`` sections, so we keep
        only those to give the AI the bean information without extraneous page
        chrome.

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
