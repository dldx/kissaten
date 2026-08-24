"""Freda Coffee scraper implementation with Shopify JSON extraction."""

import logging

from bs4 import BeautifulSoup

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="freda",
    display_name="Freda Coffee",
    roaster_name="Freda",
    website="https://freda.coffee",
    description="Freda is a micro-batch specialty coffee roaster based in Sussex, "
    "roasting weekly on a Loring and packing at sister company Bond Street "
    "Coffee in Brighton, with a curated range of direct-trade single origins.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class FredaScraper(ShopifyJsonScraper):
    """Scraper for Freda Coffee (freda.coffee) using Shopify products.json.

    NOTE: freda.coffee is the live domain (Shopify). The "fredacoffee.com"
    domain mentioned in older listings does not exist / is DNS dead.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Freda Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Freda",
            base_url="https://freda.coffee",
            products_json_urls=["https://freda.coffee/collections/all-coffee-copy/products.json"],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Pin GBP (verified live: Shopify.currency = {"active":"GBP"}).
        # The geo-detected market can serve converted prices to datacenter IPs,
        # so never let the detected value override the store currency.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Defensive exclusions. The "all-coffee-copy" (Coffee Beans) collection
        # currently holds exactly the curated single origins; subscriptions and
        # equipment live in their own collections, but keep the guards in case
        # new products join this collection later.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "office",
            "filter-papers",
            "aero",
            "hario",
            "v60",
            "orea",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Freda product URLs to the canonical form.

        Freda's canonical product pages are https://freda.coffee/products/<handle>
        (the site navigation links directly to this form). The scraper builds
        collection-prefixed URLs from the products.json base, so strip the
        collection segment here.

        Examples:
            https://freda.coffee/collections/all-coffee-copy/products/black-dog
                -> https://freda.coffee/products/black-dog
        """
        if "/collections/" in url and "/products/" in url:
            try:
                handle = url.split("/products/")[-1].split("?")[0]
                return f"{self.base_url}/products/{handle}"
            except Exception:
                return url
        return url

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Filter the product page HTML down to the bean detail accordions.

        Freda hides origin/process/variety/tasting notes/SCA score/story and
        transparency data behind collapsible ``div.product__accordion``
        sections (Info / Story / Transparency), so we keep only those to give
        the AI the bean information without extraneous page chrome.

        The Shopify product JSON (name/variants/prices) is injected into the
        returned soup's ``body`` by ShopifyJsonScraper AFTER this hook returns,
        so keeping a valid body preserves that data.
        """
        accordions = soup.select("div.product__accordion")
        if not accordions:
            return soup

        minimal = BeautifulSoup("<html><head></head><body></body></html>", "html.parser")
        for accordion in accordions:
            minimal.body.append(accordion)
        return minimal
