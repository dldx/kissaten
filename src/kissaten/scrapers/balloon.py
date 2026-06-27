"""Balloon Coffee Roasters scraper implementation with Shopify JSON extraction."""

import logging

from bs4 import BeautifulSoup, Tag

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="balloon",
    display_name="Balloon Coffee Roasters",
    roaster_name="Balloon Coffee Roasters",
    website="https://balloon.coffee",
    description="Swiss specialty coffee roaster based in Zurich, focused on sustainably sourced, organic-certified single-origin coffees roasted with curiosity and care",
    requires_api_key=True,
    currency="CHF",
    country="Switzerland",
    status="available",
)
class BalloonCoffeeRoastersScraper(ShopifyJsonScraper):
    """Scraper for Balloon Coffee Roasters (balloon.coffee) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Balloon Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Balloon Coffee Roasters",
            base_url="https://balloon.coffee",
            products_json_urls=[
                "https://balloon.coffee/collections/coffee/products.json",
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
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup | Tag:
        """Limit extraction to the main product section + flavour marquee.

        Balloon's product page renders accordions (Flavour profile, Technical
        Information, Roasting Schedule) via Alpine.js with x-show="open". The
        closed accordions are still present in the DOM but hidden, and a
        <noscript> block mirrors the same content for no-JS users. The product
        page is heavy with header/sidebar/footer/recommendations cruft that
        wastes AI tokens and can confuse extraction, so we strip everything
        outside the main product section and the marquee that carries the
        tasting notes.
        """
        # Keep only the <main id="MainContent"> subtree and drop header,
        # sidebar, footer, popup, etc.
        main = soup.find("main", id="MainContent")
        if not main:
            return soup

        # Drop the product recommendations section (irrelevant and noisy).
        for rec in main.find_all(attrs={"data-section-type": "product-recommendations"}):
            rec.decompose()

        # Build a new soup containing only the main product section and the
        # marquee section that follows it (carrying tasting notes like
        # "Lemongrass • Melon • Milk chocolate").
        new_body = BeautifulSoup("<body></body>", "lxml")
        product_section = main.find(attrs={"data-section-type": "product"})
        if product_section:
            # Wrap the product section so we keep its parent <div class="shopify-section">.
            product_wrapper = product_section.find_parent("div", class_="shopify-section")
            if product_wrapper:
                new_body.append(product_wrapper.__copy__())

        # The marquee is the next shopify-section after the main product section.
        marquee = main.find("div", class_="marquee-container")
        if marquee:
            marquee_wrapper = marquee.find_parent("div", class_="shopify-section")
            if marquee_wrapper:
                new_body.append(marquee_wrapper.__copy__())

        # The Shopify product JSON injected by shopify_base (with the rich
        # description, tags, variants, etc.) is appended at the very end so it
        # is always present in the soup the AI sees.
        return new_body