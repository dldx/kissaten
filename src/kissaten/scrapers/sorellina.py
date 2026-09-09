"""Sorellina Coffee scraper implementation with Shopify JSON extraction."""

import logging

from bs4 import BeautifulSoup

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="sorellina",
    display_name="Sorellina",
    roaster_name="Sorellina Coffee",
    website="https://sorellina.ca",
    description="Edmonton-based Canadian specialty coffee roaster focused on terroir-driven "
    "single origins, with a small rotating catalogue organised into Terroir, "
    "Grower, and Innovation tiers plus a rare 'Brewers Series' for tiny competition lots",
    requires_api_key=True,
    currency="CAD",
    country="Canada",
    status="available",
)
class SorellinaScraper(ShopifyJsonScraper):
    """Scraper for Sorellina Coffee (sorellina.ca) using Shopify products.json.

    Sorellina runs a deliberately small catalogue (~7 coffee products at a
    time). The Shopify ``products.json`` payload carries only the title,
    tags, and size-variant prices — ``body_html`` is empty — so all bean
    detail (producer, farm, origin region, altitude, varietal, process,
    aroma/flavour/tactile notes) lives in a "PEOPLE, PLACE, PROCESS" spec
    table that only exists on the rendered product page. We therefore scrape
    product pages and prune them to the main product section before AI
    extraction.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Sorellina scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Sorellina Coffee",
            base_url="https://sorellina.ca",
            products_json_urls=["https://sorellina.ca/collections/allcoffee/products.json"],
            scrape_product_pages=True,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # The curated /collections/allcoffee collection already limits the
        # catalogue to coffee (beans + one instant coffee); only the Shopify
        # gift card needs filtering out. Extra entries guard against the
        # collection ever mixing in the equipment/merch that lives in
        # /collections/all (grinders, brew ware, cups).
        self.exclude_slugs = [
            "gift-card",
            "gift",
            "subscription",
            "wholesale",
            "grinder",
            "ceado",
            "origami",
            "brewer",
            "kettle",
            "scale",
            "equipment",
            "merch",
            "apparel",
            "mug",
            "tumbler",
            "hoodie",
            "tshirt",
        ]

        # Currency geolocation guard: the store runs Shopify Markets and can
        # serve geo-converted prices (the footer country selector offers GBP,
        # EUR, USD, ... markets). Pin the home currency so a datacenter-IP
        # fetch can never stamp converted prices onto beans.
        self.store_currency = "CAD"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Sorellina URLs by removing collection segments.

        The site's canonical product URLs are the no-collection form
        (``/products/<handle>``), which is what the storefront links to.

        Args:
            url: Original product URL

        Returns:
            Preprocessed product URL
        """
        if "/collections/" in url and "/products/" in url:
            # e.g. https://sorellina.ca/collections/allcoffee/products/slug
            #   -> https://sorellina.ca/products/slug
            try:
                handle = url.split("/products/")[-1].split("?")[0]
                return f"{self.base_url}/products/{handle}"
            except Exception:
                return url
        return url

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Prune the product page to the main product section.

        Sorellina's product pages put all bean information (title, price,
        size variants, the "PEOPLE, PLACE, PROCESS" spec table with
        producer/farm/origin/altitude/varietal/process, and the SENSORY
        aroma/flavour/tactile rows) inside a single ``shopify-section``
        whose id ends in ``__main``. Everything else on the page is noise:
        scrolling announcement marquees, a footer with a ~200-entry country
        selector, and navigation chrome.

        We build a new minimal soup WITH a body: ShopifyJsonScraper injects
        the Shopify JSON context (name/price/variants) at the top of
        ``soup.body`` AFTER this hook returns, so keeping a valid body
        preserves that data.

        Args:
            soup: BeautifulSoup object of the product page

        Returns:
            Pruned BeautifulSoup object
        """
        main_sections = [
            div for div in soup.select('div[id^="shopify-section-"]') if div.get("id", "").endswith("__main")
        ]
        if not main_sections:
            return soup

        minimal = BeautifulSoup("<html><head></head><body></body></html>", "html.parser")
        for section in main_sections:
            minimal.body.append(section)
        return minimal
