"""Portebleue scraper implementation with Shopify JSON extraction."""

import logging

from bs4 import BeautifulSoup

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="porte-bleue",
    display_name="Portebleue",
    roaster_name="Portebleue",
    website="https://portebleue.ca",
    description="Small-batch specialty coffee roaster based in Montréal, Québec, roasting "
    "sustainably sourced single origins to order on a P3000 hot-air roaster",
    requires_api_key=True,
    currency="CAD",
    country="Canada",
    status="available",
)
class PorteBleueScraper(ShopifyJsonScraper):
    """Scraper for Portebleue (portebleue.ca) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Portebleue scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Portebleue",
            base_url="https://portebleue.ca",
            products_json_urls=["https://portebleue.ca/collections/coffee/products.json"],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # The storefront is CAD-only (Shopify.currency "CAD" rate 1.0, single
        # Canadian market). Pin CAD so a geo-localized storefront (which Shopify
        # can serve to non-local clients) can't convert prices.
        self.store_currency = "CAD"
        self._currency_detected = True

        # /collections/coffee is a curated bean-only collection, but keep a
        # small exclude list as a safety net against future non-coffee items.
        # Do NOT add sampler/tasting-kit exclusions: those products must flow
        # through with is_tasting_kit/requires_review flags instead.
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
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Portebleue URLs by removing collection segments.

        The site's canonical product URLs have no collection segment
        (e.g. https://portebleue.ca/products/gloria-ortega).
        """
        if "/collections/" in url and "/products/" in url:
            try:
                handle = url.split("/products/")[-1].split("?")[0]
                return f"{self.base_url}/products/{handle}"
            except Exception:
                return url
        return url

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Filter the product page HTML down to the bean-relevant sections.

        Portebleue product pages carry the fields the products.json payload
        lacks inside a collapsed "Coffee Details" accordion (Variety, Process,
        Producer, Country, Tasting Notes, Roast Level), plus the farm/story
        description and the tasting-notes subtitle. Keep only the product info
        column (title, subtitle, price, accordion, description) so the AI gets
        the bean data without the page chrome, recommendations, and footer.

        We build a new minimal soup WITH a body: ShopifyJsonScraper injects
        the Shopify JSON context (name/price/variants) at the top of
        ``soup.body`` AFTER this hook returns, so keeping a valid body
        preserves that data.
        """
        info = soup.select_one("div.product__info-wrapper")
        if info is not None:
            candidates = [info]
        else:
            # Fallback: keep the individual bean-data sections.
            candidates = [
                el
                for sel in ("div.product__accordion", "div.product__description", "div.product__title")
                for el in soup.select(sel)
            ]

        if not candidates:
            return soup

        minimal = BeautifulSoup("<html><head></head><body></body></html>", "html.parser")
        for candidate in candidates:
            minimal.body.append(candidate)
        return minimal
