"""Blossom Coffee Roasters (UK) scraper implementation with Shopify JSON extraction.

Blossom Coffee Roasters is a UK specialty coffee roaster based in Cardiff,
shipping across the UK. NOTE: this is the UK roaster at blossomcoffee.co.uk,
NOT the US "Blossom Coffee Roasters" on Vashon Island.
"""

import logging

from bs4 import BeautifulSoup

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="blossom",
    display_name="Blossom",
    roaster_name="Blossom",
    website="https://blossomcoffee.co.uk",
    description="UK specialty coffee roaster based in Cardiff, sourcing single-origin "
    "coffees from Colombia, Guatemala and beyond, roasted in small batches "
    "with a focus on transparency and long-term producer relationships",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class BlossomScraper(ShopifyJsonScraper):
    """Scraper for Blossom Coffee Roasters (blossomcoffee.co.uk) using Shopify products.json.

    The coffee catalogue lives in the curated ``/collections/coffee`` collection
    (8 products). The products.json ``body_html`` is empty for every coffee, so
    product pages are scraped with ``use_optimized_mode=False`` and the soup is
    pruned to the bean-detail accordions and description blocks.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Blossom Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Blossom",
            base_url="https://blossomcoffee.co.uk",
            products_json_urls=["https://blossomcoffee.co.uk/collections/coffee/products.json"],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Pin GBP so Shopify's geo-located market detection can't override it.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Exclude non-coffee products by slug (subscriptions, gift cards,
        # equipment, merch, etc.). No sampler/taster-pack entries: a tasting-kit
        # product that ever appears here must be flagged, not excluded.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "mug",
            "tumbler",
            "hoodie",
            "tshirt",
            "v60",
            "timemore",
            "chemex",
            "aeropress",
            "filter-papers",
            "apparel",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Blossom product URLs by removing the collection segment.

        The base class builds URLs from the products.json base
        (e.g. ``/collections/coffee/products/<handle>``), but the live site's
        canonical product pages are just ``/products/<handle>`` (no collection
        segment) — both resolve 200, but the collection-less form matches the
        site's real URLs.
        """
        if "/collections/" in url and "/products/" in url:
            # e.g. https://blossomcoffee.co.uk/collections/coffee/products/handle
            #   -> https://blossomcoffee.co.uk/products/handle
            try:
                handle = url.split("/products/")[-1].split("?")[0]
                return f"{self.base_url}/products/{handle}"
            except Exception:
                return url
        return url

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Filter the product page HTML down to the bean-detail sections.

        Blossom hides origin/process/variety/tasting notes behind collapsible
        ``<details>`` accordions (About this coffee / Relationship /
        Transparency) and a metafield description block that parses the title
        teaser, blend breakdown and long-form story. The product name/price
        variants already come from the injected Shopify JSON, so we keep only
        these sections to give the AI the bean information without the page
        chrome.

        We build a minimal soup WITH a body: ShopifyJsonScraper injects the
        Shopify JSON context at the top of ``soup.body`` AFTER this hook
        returns, so a valid body preserves that data.
        """
        keep = []
        keep.extend(soup.select("div.info-accordion__inner"))
        keep.extend(soup.select("div.metafield-rich_text_field"))

        if not keep:
            return soup

        minimal = BeautifulSoup("<html><head></head><body></body></html>", "html.parser")
        for part in keep:
            minimal.body.append(part)
        return minimal
