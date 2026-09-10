"""Terroir Laboratory scraper implementation with Shopify JSON extraction."""

import logging

from bs4 import BeautifulSoup

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="terroir-laboratory",
    display_name="Terroir Laboratory",
    roaster_name="Terroir Laboratory",
    website="https://terroiridn.com",
    description="Indonesian specialty coffee roaster (TERROIR.IDN by Terroirlab) based in "
    "Tangerang, Banten, known for experimental fermentation lots and competition-grade "
    "single origins such as Best of Panama",
    requires_api_key=True,
    currency="IDR",
    country="Indonesia",
    status="available",
)
class TerroirLaboratoryScraper(ShopifyJsonScraper):
    """Scraper for Terroir Laboratory (terroiridn.com) using Shopify products.json.

    The storefront is localized under ``/en`` but canonical product URLs are
    the plain ``/products/<handle>`` form, so ``preprocess_product_url`` strips
    the localized collection segment. Bean details (blend components, roast
    level, recommended brew, tasting notes) live in collapsed accordion
    sections on the product page rather than in ``products.json``, so product
    pages are scraped with the soup pruned to the product-information block.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Terroir Laboratory scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Terroir Laboratory",
            base_url="https://terroiridn.com",
            products_json_urls=["https://terroiridn.com/en/collections/all/products.json"],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude non-coffee products (apparel, merch, gift cards, etc.)
        self.exclude_slugs = [
            "t-shirt",
            "gift-card",
            "gift",
            "subscription",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "mug",
            "tumbler",
            "apparel",
        ]

        # Pin the home currency: the store is IDR-only and Shopify Markets
        # must not geo-convert prices for datacenter-IP requests.
        self.store_currency = "IDR"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Terroir Laboratory product URLs.

        The store serves canonical product pages at ``/products/<handle>``;
        the ``/en/collections/all`` segment from the products.json base must
        be stripped so URLs match the site's real product URLs.
        """
        marker = "/products/"
        idx = url.find(marker)
        if idx != -1:
            return f"{self.base_url}{url[idx:]}"
        return url

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Limit extraction to the product information section.

        The blend components, roast level, recommended brew and tasting notes
        live in collapsed ``<details>`` accordions inside the
        ``div.product-information`` section; everything else (nav, footer,
        recommendations, cookie banner) is noise for the AI extractor.
        """
        info = soup.select_one("div.product-information")
        if info:
            logger.debug("Limiting extraction to div.product-information")
            return info
        return soup
