"""BlendIn Coffee Club scraper implementation with Shopify JSON extraction."""

import logging

from bs4 import BeautifulSoup

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="blendin-coffee-club",
    display_name="BlendIn Coffee Club",
    roaster_name="Blendin Coffee Club",
    website="https://blendincoffeeclub.com",
    description="US specialty coffee roaster based in Sugar Land, Texas, recognized among "
    "the World's 100 Best Coffee Shops and source of the 2024 US Brewers Cup "
    "Champion's winning coffee",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="available",
)
class BlendinCoffeeClubScraper(ShopifyJsonScraper):
    """Scraper for BlendIn Coffee Club (blendincoffeeclub.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize BlendIn Coffee Club scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Blendin Coffee Club",
            base_url="https://blendincoffeeclub.com",
            products_json_urls=[
                "https://blendincoffeeclub.com/collections/coffee/products.json",
            ],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # The curated /collections/coffee endpoint already limits to beans, but
        # keep a defensive exclusion list for any non-coffee / subscription
        # handles that may appear.
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
            "cold-brew-cans",
            "easy-pour",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize BlendIn product URLs to the canonical /products/<handle> form.

        The site's canonical product URLs (from its canonical link tags and
        product sitemap) omit the collection segment.
        """
        if "/collections/" in url and "/products/" in url:
            try:
                handle = url.split("/products/")[-1].split("?")[0]
                return f"{self.base_url}/products/{handle}"
            except Exception:
                pass
        return url

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Limit extraction to the product description and origin-details sections.

        The grid layout interleaves media and text; the bean details live in the
        ``bic-archive-detail`` (title, origin country, description, roast profile,
        flavor notes) and ``bic-pdp-origin`` (structured Origin Details) blocks.
        Keeping just these keeps AI token usage low while preserving the data the
        products.json payload lacks.
        """
        prune_me = BeautifulSoup("<html><body></body></html>", "lxml")

        for selector in (".bic-archive-detail", ".bic-pdp-origin"):
            for el in soup.select(selector):
                prune_me.body.append(el.extract())

        # Fall back to the original soup if nothing matched.
        if not prune_me.body.contents:
            return soup
        return prune_me
