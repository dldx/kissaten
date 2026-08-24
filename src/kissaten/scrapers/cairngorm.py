"""Cairngorm Coffee scraper implementation with Shopify JSON extraction.

Cairngorm is an Edinburgh-based specialty coffee roaster (cairngorm.coffee).
This scraper uses the curated ``coffee`` collection's products.json for
discovery and stock status, then AI-extracts bean detail from the rendered
product page. The product page carries bean fields that the products.json
``body_html`` does not (Producer/Origin/Process/Variety/Growing Altitude), so
we scrape product pages and prune the soup to the two sections that hold the
useful content: ``safe-sticky.product-info`` (title, tasting notes, price,
description) and ``section.coffee-info-columns-section`` (the origin info
columns). Currency is pinned to GBP because the store is UK-based.
"""

import logging

from bs4 import BeautifulSoup

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="cairngorm",
    display_name="Cairngorm Coffee",
    roaster_name="Cairngorm",
    website="https://cairngorm.coffee",
    description="Edinburgh-based specialty coffee roaster known for high-quality "
    "single origin coffees and thoughtful sourcing",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class CairngormScraper(ShopifyJsonScraper):
    """Scraper for Cairngorm Coffee (cairngorm.coffee) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Cairngorm Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Cairngorm",
            base_url="https://cairngorm.coffee",
            products_json_urls=["https://cairngorm.coffee/collections/coffee/products.json"],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Pin currency to GBP (store is UK-based; prevents geolocation conversion).
        self.store_currency = "GBP"
        self._currency_detected = True

        # Exclude non-coffee products in the curated collection. Cascara is a
        # coffee-cherry tea (a non-bean beverage) and subscriptions are not beans.
        # Tasting kits (e.g. the cupping box set) are intentionally NOT excluded;
        # they are kept and flagged for review via _apply_product_flags.
        self.exclude_slugs = [
            "subscription",
            "cascara",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def _get_excluded_url_patterns(self) -> list[str]:
        """Drop the base ``cupping`` pattern so the cupping sample box set is kept.

        The base exclusion treats ``cupping`` as a workshop/ticket and would drop
        ``cupping-box-set``, but on this store that handle is a physical sample
        box (a curated tasting kit) that must be retained and flagged rather than
        excluded.
        """
        patterns = super()._get_excluded_url_patterns()
        return [p for p in patterns if p != "cupping"]

    def _get_tasting_kit_url_patterns(self) -> list[str]:
        """Flag Cairngorm's cupping/sample box set as a curated tasting kit."""
        return super()._get_tasting_kit_url_patterns() + ["cupping-box", "sample-box"]

    def preprocess_product_url(self, url: str) -> str:
        """Canonicalize Cairngorm product URLs to the site's real form.

        The store serves live product pages at ``/products/<handle>`` (no
        collection segment). The base class builds collection-prefixed URLs from
        the products.json base, so strip the ``/collections/coffee`` segment.
        """
        return url.replace("/collections/coffee", "")

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Prune the product page to just the informative sections.

        Keeps ``safe-sticky.product-info`` (title, tasting notes, price,
        description) and ``section.coffee-info-columns-section`` (Producer,
        Origin, Process, Variety, Growing Altitude) for token-efficient AI
        extraction, discarding images, nav, and recommendation boilerplate.
        """
        new_soup = BeautifulSoup("<html><body></body></html>", "lxml")
        body = new_soup.body

        product_info = soup.find("safe-sticky", class_=lambda c: c and "product-info" in c)
        if product_info:
            body.append(product_info.extract())

        info_columns = soup.find("section", class_=lambda c: c and "coffee-info-columns-section" in c)
        if info_columns:
            body.append(info_columns.extract())

        if body.find_all(True):
            logger.debug("Pruned Cairngorm product page to product-info + info-columns sections")
            return new_soup
        return soup
