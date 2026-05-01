"""Assembly Coffee scraper implementation with Shopify JSON extraction."""

import logging

from ..schemas import CoffeeBean
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="assembly-coffee",
    display_name="Assembly Coffee",
    roaster_name="Assembly Coffee London",
    website="https://assemblycoffee.co.uk",
    description="Award-winning specialty coffee roastery founded in 2015 and based in Brixton, London",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class AssemblyCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Assembly Coffee (assemblycoffee.co.uk) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Assembly Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Assembly Coffee London",
            base_url="https://assemblycoffee.co.uk",
            products_json_urls=[
                "https://assemblycoffee.co.uk/collections/buy-coffee/products.json",
            ],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=1.5,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Exclude non-coffee products or sample packs
        self.exclude_slugs = [
            "discovery",
            "sample-pack",
            "house-selection",
            "cofffee-pods",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Assembly Coffee product URLs.

        Assembly URLs in collections often include collection paths,
        but the canonical product URLs are top-level.
        """
        if "/collections/" in url and "/products/" in url:
            # Extract just the /products/part
            import re

            match = re.search(r"(/products/[^/?#]+)", url)
            if match:
                return self.resolve_url(match.group(1))
        return url

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Override to detect roast profile from Shopify tags if available."""
        url_str = str(bean.url)
        # Check if we can infer roast from URL constraints or tags (handled by AI usually)
        if "brew_espresso" in url_str:
            bean.roast_profile = "Espresso"
        elif "brew_Pour_Over" in url_str:
            bean.roast_profile = "Filter"

        return super().postprocess_extracted_bean(bean)
