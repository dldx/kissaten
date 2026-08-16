"""Zest Coffee scraper implementation with Shopify JSON extraction."""

import logging

from bs4 import BeautifulSoup

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="zest",
    display_name="Zest",
    roaster_name="Zest",
    website="https://www.zestcoffee.com.au",
    description="Australian specialty coffee roaster based in Brisbane, Queensland, "
    "known for single origin, blends and a curated foundation series of roasted beans.",
    requires_api_key=True,
    currency="AUD",
    country="Australia",
    status="available",
)
class ZestCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Zest Coffee (zestcoffee.com.au) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Zest Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Zest",
            base_url="https://www.zestcoffee.com.au",
            products_json_urls=[
                "https://www.zestcoffee.com.au/collections/coffee/products.json",
            ],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude non-whole-bean coffee products from the curated coffee collection:
        # subscriptions, cold brew concentrate, drip bags and tasting sets.
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
            "cold-brew",
            "drip-bags",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Zest product URLs to the canonical /products/<handle> form.

        The curated ``/collections/coffee`` products.json yields the collection-form
        URL (``/collections/coffee/products/<handle>``), but Zest serves product pages
        at the no-collection form (``/products/<handle>``).
        """
        marker = "/collections/coffee/products/"
        if marker in url:
            return url.replace(marker, "/products/")
        return url

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Filter the product page HTML down to the product container.

        Zest renders producer/farm/region/varietal/process/altitude details inside
        ``div.product-container`` (tab panels) which is all the information the
        products.json body_html lacks, so we keep only that container to give the
        AI the rich bean details without the full page markup.

        We build a new minimal soup WITH a body: ShopifyJsonScraper injects the
        Shopify JSON context (name/price/variants) at the top of ``soup.body``
        AFTER this hook returns, so keeping a valid body preserves that data.
        """
        container = soup.select_one("div.product-container")
        if not container:
            return soup

        minimal = BeautifulSoup("<html><head></head><body></body></html>", "html.parser")
        minimal.body.append(container)
        return minimal
