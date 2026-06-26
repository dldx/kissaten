"""Picolot scraper implementation with Shopify JSON extraction."""

import logging
import re
from typing import Any

from bs4 import BeautifulSoup

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)

_BAG_SIZE_RE = re.compile(
    r"(?:Quantity|Bag\s*Size)\s*[:：]\s*(\d+(?:\.\d+)?)\s*(?:grams?|g)\b",
    re.IGNORECASE,
)
_MIN_BAG_GRAMS = 15
_MAX_BAG_GRAMS = 2000


@register_scraper(
    name="picolot",
    display_name="Picolot",
    roaster_name="Picolot",
    website="https://picolot.shop",
    description="A curation of extremely tiny lots and interesting beans",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="available",
)
class PicolotScraper(ShopifyJsonScraper):
    """Scraper for Picolot (picolot.shop) using Shopify products.json.

    Scrapes both the main catalog and the coffee-archive collection so that
    past roasts are still discoverable, then deduplicates products by
    normalizing every handle to the canonical /products/{handle} URL.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Picolot scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Picolot",
            base_url="https://picolot.shop",
            products_json_urls=[
                "https://picolot.shop/products.json",
                "https://picolot.shop/collections/coffee-archive/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "melodrip",
            "tasting-set",
            "cupping-kit",
            "garage-sale",
            "founding-membership",
            "membership",
            "combo",
            "bundle",
            "sampler",
            "taster-pack",
            "top-",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Normalize Picolot product URLs to /products/{handle}.

        The coffee-archive products.json produces URLs like
        ``/collections/coffee-archive/products/{handle}`` and the main
        products.json produces ``/products/{handle}``. We collapse both to
        the canonical non-collection form so that archive and catalog
        entries for the same product share a single URL and are naturally
        deduplicated.

        Args:
            url: Product URL produced by the base scraper

        Returns:
            Canonical product URL at ``/products/{handle}``
        """
        if "/products/" not in url:
            return url

        handle = url.split("/products/")[-1].rstrip("/")
        return f"{self.base_url}/products/{handle}"

    @staticmethod
    def _parse_bag_size_from_body(body_html: str | None) -> int | None:
        """Extract the bag weight in grams from a Shopify body_html string.

        Picolot consistently states the actual bag size in the product body
        under ``<strong>Quantity:</strong> Xg`` or
        ``<strong>Bag Size:</strong> Xg``. The variant ``grams`` field in
        their products.json is unreliable, so we parse the body text instead.

        Args:
            body_html: Raw HTML body of a Shopify product

        Returns:
            Integer bag weight in grams, or ``None`` if no value was found
            or it fell outside the sanity range of 15–2000 g.
        """
        if not body_html:
            return None

        plain = BeautifulSoup(body_html, "lxml").get_text(" ", strip=True)
        match = _BAG_SIZE_RE.search(plain)
        if not match:
            return None

        grams = int(float(match.group(1)))
        if grams < _MIN_BAG_GRAMS or grams > _MAX_BAG_GRAMS:
            logger.debug("Bag size %sg from body is outside sanity range; ignoring", grams)
            return None

        return grams

    async def _fetch_all_shopify_products(self, products_json_url: str) -> list[dict[str, Any]]:
        """Fetch all products and rewrite variant weights from body_html.

        Picolot's variant ``grams`` field is unreliable. The roaster states
        the actual bag size in the product body as ``Quantity: Xg`` or
        ``Bag Size: Xg``. When we can parse that value, we overwrite the
        ``grams``, ``weight`` and ``weight_unit`` fields on every variant so
        the AI extractor sees only the correct weight. Products whose body
        has no bag-size statement are left untouched (no regression vs.
        previous behavior).

        Args:
            products_json_url: URL to the products.json endpoint

        Returns:
            List of product dictionaries with corrected variant weights
        """
        products = await super()._fetch_all_shopify_products(products_json_url)

        patched = 0
        for product in products:
            bag_size = self._parse_bag_size_from_body(product.get("body_html"))
            if bag_size is None:
                continue

            variants = product.get("variants") or []
            if not variants:
                continue

            for variant in variants:
                variant["grams"] = bag_size
                variant["weight"] = bag_size / 1000
                variant["weight_unit"] = "kg"

            patched += 1
            logger.debug("Patched %s variants to %dg from body_html", len(variants), bag_size)

        if patched:
            logger.info("Patched variant weights from body_html for %d Picolot products", patched)

        return products
