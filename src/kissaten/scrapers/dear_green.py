"""Dear Green Coffee scraper implementation with Shopify JSON extraction."""

import logging

from bs4 import BeautifulSoup

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="dear-green",
    display_name="Dear Green",
    roaster_name="Dear Green",
    website="https://deargreencoffee.com",
    description="Glasgow-based specialty coffee roaster, certified B-Corp, sourcing "
    "fully traceable and ethically sourced coffees from producers who share their values.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class DearGreenScraper(ShopifyJsonScraper):
    """Scraper for Dear Green Coffee (deargreencoffee.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Dear Green Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Dear Green",
            base_url="https://deargreencoffee.com",
            products_json_urls=[
                "https://deargreencoffee.com/collections/all/products.json"
            ],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude non-coffee products (subscriptions, gift cards, equipment, etc.)
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
            # Dear Green-specific non-coffee / equipment / book / class handles
            "grinder",  # aergrind-hand-grinder-made-by-knock
            "aeropress",  # Aerobie AEROPRESS brewers, filters, bundles
            "chemex",  # CHEMEX brewers, filters, bundles
            "masterclass",  # espresso-masterclass(-group)
            "kit",  # coffee-cupping-kit, brewing bundles
            "class",  # coffee-lovers-coffee-brew-class
            "coffee-creations",  # coffee brewing recipe book
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Filter the product page HTML down to the description + bean spec sheet.

        Dear Green renders a structured ``ul.metafields-list`` (profile, harvest,
        process, variety, altitude, area, country, sourcing partner) directly
        inside the ``div.description`` element. This structured spec is NOT in
        the Shopify products.json body_html, so we keep just the description
        block (prose + spec sheet) to give the AI the bean information without
        the surrounding page chrome.

        We build a new minimal soup WITH a body: ShopifyJsonScraper injects the
        Shopify JSON context (name/price/variants) at the top of ``soup.body``
        AFTER this hook returns, so keeping a valid body preserves that data.
        """
        desc = soup.select_one("div.description")
        if not desc:
            return soup

        minimal = BeautifulSoup(
            "<html><head></head><body></body></html>", "html.parser"
        )
        minimal.body.append(desc)
        return minimal
