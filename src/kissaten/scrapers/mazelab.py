"""Mazelab coffee scraper implementation with AI-powered extraction."""

import logging

import logfire
from bs4 import BeautifulSoup

from ..ai import CoffeeDataExtractor
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)
logfire.configure(scrubbing=False)

@register_scraper(
    name="mazelab-coffee",
    display_name="Mazelab Coffee",
    roaster_name="Mazelab Coffee",
    website="https://mazelabcoffee.com",
    description="Specialty coffee roaster based in Prague, Czech Republic",
    requires_api_key=True,
    currency="CZK",
    country="Czechia",
    status="available",
)
class MazelabCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Mazelab Coffee using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Mazelab Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Mazelab Coffee",
            base_url="https://mazelabcoffee.com",
            products_json_urls=[
                "https://mazelabcoffee.com/collections/coffee/products.json",
            ],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Strip the origin and about sections down to plain text to minimise AI tokens."""
        origin_map = soup.select_one("section.section--coffee-origin-map")
        about = soup.select_one("section.section--coffee-about")
        if not origin_map or not about:
            return soup

        origin_text = origin_map.get_text("\n", strip=True)
        about_text = about.get_text("\n", strip=True)
        simplified_html = f"<section id='origin-map'>{origin_text}</section><section id='about'>{about_text}</section>"
        return BeautifulSoup(simplified_html, "html.parser")
