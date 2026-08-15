"""Philocoffea scraper implementation with Shopify JSON extraction.

Philocoffea is the specialty coffee brand of Tetsu Kasuya (2016 World
Brewers Cup Champion), based in Tokyo, Japan. The store is a Shopify
storefront (en.philocoffea.com) and exposes a curated /collections/coffee
collection whose product JSON carries rich bean detail (flavor notes, farm,
producer, altitude, varietal, processing, roast level), so a JSON-only scrape
mode is sufficient and cheapest.

Note on currency: the store is denominated in JPY but Shopify's automatic
localization serves price-converted pages/products.json (e.g. GBP) depending
on the request's Accept-Language header. We pin ``currency=JPY`` on every
products.json page request so the injected JSON context carries the canonical
JPY prices.
"""

import logging
from typing import Any

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="philocoffea",
    display_name="Philocoffea",
    roaster_name="Philocoffea",
    website="https://en.philocoffea.com",
    description="Specialty coffee by Tetsu Kasuya (2016 World Brewers Cup Champion), "
    "based in Tokyo, Japan. Known for innovative single origins and the signature "
    "dip-style coffee.",
    requires_api_key=True,
    currency="JPY",
    country="Japan",
    status="available",
)
class PhilocoffeaScraper(ShopifyJsonScraper):
    """Scraper for Philocoffea (en.philocoffea.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Philocoffea scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Philocoffea",
            base_url="https://en.philocoffea.com",
            products_json_urls=["https://en.philocoffea.com/collections/coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # The curated coffee collection is already coffee-specific; exclude any
        # residual non-coffee items just in case.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merch",
            "merchandise",
            "taster-pack",
            "paper-bags",
            "tenugui",
            "filter",
            "book",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Strip the collection segment to match the store's canonical product URLs.

        The products.json base URL is /collections/coffee/, so the generated
        product URLs include that segment. The store's real/canonical product
        pages are the no-collection form /products/<handle>, so we normalize.
        """
        return url.replace("/collections/coffee/products/", "/products/")

    async def _fetch_all_shopify_products(self, products_json_url: str) -> list[dict[str, Any]]:
        """Fetch all products from the products.json endpoint pinned to JPY.

        Shopify's automatic localization converts product prices (e.g. to GBP)
        based on the request's Accept-Language header. The shop's canonical
        currency is JPY, so we append ``currency=JPY`` to every page request;
        otherwise the AI-extracted prices would be poisoned conversion values.
        Otherwise this mirrors the base pagination ladder (httpx then
        Playwright on 429), including the failed-listing guard.
        """
        all_products = []
        page = 1
        limit = 250

        while True:
            url = f"{products_json_url}?currency=JPY&limit={limit}&page={page}"
            logger.info(f"Fetching Shopify products: {url}")

            data, _ = await self._fetch_page_with_escalation(url)
            if data is None:
                # Listing fetch failed for this page; record it and stop
                # paginating (later pages would only compound the failure).
                if products_json_url not in self._failed_listing_urls:
                    self._failed_listing_urls.append(products_json_url)
                break

            products = data.get("products", [])
            if not products:
                break

            all_products.extend(products)
            logger.debug(f"Fetched {len(products)} products from page {page}")

            if len(products) < limit:
                break

            page += 1

        return all_products

    def _extract_currency_from_html(self, soup: object) -> str | None:
        """Force the store currency to JPY.

        Philocoffea is a Tokyo-based roaster whose products.json prices are
        denominated in Japanese Yen. Shopify's automatic geo/localization
        serves a converted currency (e.g. GBP) depending on the request's
        Accept-Language header, which would otherwise poison the extracted
        price. The store's canonical currency is JPY regardless.
        """
        return "JPY"
