"""Tandem Coffee scraper implementation with Shopify JSON extraction."""

import logging

from bs4 import BeautifulSoup

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="tandem",
    display_name="Tandem",
    roaster_name="Tandem",
    website="https://www.tandemcoffee.com",
    description="Specialty coffee roaster based in Portland, Maine, focused on approachable "
    "espresso-forward coffee, seasonal single origins, and classic blends.",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="available",
)
class TandemScraper(ShopifyJsonScraper):
    """Scraper for Tandem Coffee Roasters (tandemcoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Tandem Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Tandem",
            base_url="https://www.tandemcoffee.com",
            products_json_urls=["https://www.tandemcoffee.com/collections/coffees/products.json"],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # The coffees collection mixes in instant coffee and subscriptions
        # alongside the bean catalogue, so exclude those by slug.
        self.exclude_slugs = [
            "subscription",
            "instant",
            "gift-card",
            "gift",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Strip the collection segment from product URLs.

        The site's canonical product pages are ``https://www.tandemcoffee.com/products/<handle>``
        (no collection segment), so normalize ShopifyJsonScraper's generated
        ``/collections/coffees/products/<handle>`` form to match the real URLs.
        """
        if "/collections/" in url and "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Prune the product page down to the bean detail block.

        Tandem keeps Varietals, Elevation, Processing, and "We hear" tasting
        notes inside ``div.prodmeta`` — information the products.json payload
        does not carry. Keep only that block (the Shopify JSON context with
        name/price/variants/description is injected afterwards), so the AI gets
        the bean details without the page chrome burning tokens.
        """
        prodmeta = soup.select_one("div.prodmeta")
        if not prodmeta:
            return soup

        # Some metafield values (e.g. the Sun Lamp decaf's "Processing" and
        # "We hear" blocks) embed a <style> tag with inline CSS in the markup.
        # Drop those so the AI sees the clean text values, not CSS noise.
        for style_tag in prodmeta.select("style"):
            style_tag.decompose()

        minimal = BeautifulSoup("<html><head></head><body></body></html>", "html.parser")
        minimal.body.append(prodmeta)
        return minimal
