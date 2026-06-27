"""Chronic Coffee scraper implementation with Shopify JSON extraction."""

import logging
from typing import Any

from bs4 import BeautifulSoup, Tag

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="chronic-coffee",
    display_name="Chronic Coffee",
    roaster_name="Chronic Coffee",
    website="https://chronic-coffee.co.uk",
    description="Swiss specialty coffee roaster based in Geneva, certified B Corp and organic, roasting specialty coffee in small batches since 2017",
    requires_api_key=True,
    currency="CHF",
    country="Switzerland",
    status="available",
)
class ChronicCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Chronic Coffee (chronic-coffee.co.uk) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Chronic Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Chronic Coffee",
            base_url="https://chronic-coffee.co.uk",
            products_json_urls=[
                "https://chronic-coffee.co.uk/collections/all/products.json",
            ],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Only keep products whose product_type is exactly "Coffee beans ".
        # Chronic's catalog is a mix of beans, equipment, accessories, gift cards,
        # discovery boxes, ready-to-drink coffees, etc. - we want only beans.
        self.allowed_product_types = {"Coffee beans "}

        # Exclude non-coffee product slugs (subscriptions, gift cards, etc.)
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
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Override to filter Chronic products by product_type.

        Returns:
            List of product URLs whose product_type is in self.allowed_product_types.
        """
        products = await self._fetch_all_shopify_products(store_url)
        found_urls = []

        for product in products:
            handle = product.get("handle")
            if not handle:
                continue

            product_type = product.get("product_type") or ""
            if self.allowed_product_types and product_type not in self.allowed_product_types:
                logger.debug(f"Skipping product type '{product_type}': {handle}")
                continue

            if any(slug in handle for slug in self.exclude_slugs):
                logger.debug(f"Skipping excluded product slug: {handle}")
                continue

            base_path = store_url.replace("/products.json", "")
            url = f"{base_path}/products/{handle}"
            url = self.preprocess_product_url(url)

            self._shopify_product_data[url] = product

            is_available = any(v.get("available", False) for v in product.get("variants", []))
            self._shopify_stock_status[url] = is_available

            if self.is_coffee_product_url(url) and self.is_coffee_product_name(product.get("title", "")):
                found_urls.append(url)

        return found_urls

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Chronic Coffee product URLs to /products/<handle>.

        Shopify builds product URLs under each collection path; we strip the
        collection segment so all products share a single canonical URL.
        """
        if "/collections/" in url and "/products/" in url:
            handle = url.split("/products/", 1)[1]
            return f"{self.base_url}/products/{handle}"
        return url

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup | Tag:
        """Limit extraction to the main product section for efficiency."""
        main = soup.find("main", id="MainContent")
        if main:
            product_section = main.find(attrs={"data-section-type": "product"})
            if product_section:
                wrapper = product_section.find_parent("div", class_="shopify-section")
                if wrapper:
                    return wrapper
        return soup