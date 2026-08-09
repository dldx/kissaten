"""La Cabra scraper implementation with Shopify JSON extraction."""

import logging

from bs4 import BeautifulSoup, Tag

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="la-cabra",
    display_name="La Cabra",
    roaster_name="La Cabra",
    website="https://lacabra.com",
    description=(
        "Modern specialty coffee roaster based in Aarhus & Copenhagen, Denmark, "
        "renowned for delicate, light roast single origin coffees."
    ),
    requires_api_key=True,
    currency="EUR",
    country="Denmark",
    status="available",
)
class LaCabraScraper(ShopifyJsonScraper):
    """Scraper for La Cabra (lacabra.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize La Cabra scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="La Cabra",
            base_url="https://lacabra.com",
            products_json_urls=["https://lacabra.com/collections/coffee/products.json"],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude non-coffee products (subscriptions, ceramics/würtz, apparel, equipment, chocolate, bundles)
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
            "-pack-",
            "apparel",
            "t-shirt",
            "tshirt",
            "tote-bag",
            "cap",
            "cup",
            "wurtz",
            "wuerz",
            "chocolate",
            "bundle",
            "server",
            "dripper",
            "scale",
            "grinder",
            "glass",
            "drops",
            "cafetto",
            "filter",
            "spoon",
            "kettle",
            "zerowater",
            "aeropress",
            "tds",
            "fellow",
            "bloom",
            "test",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize La Cabra product URLs to /products/<handle>.

        Shopify builds product URLs under collection paths; we strip the
        collection segment so all products share a single canonical URL.
        """
        if "/collections/" in url and "/products/" in url:
            handle = url.split("/products/", 1)[1]
            return f"{self.base_url}/products/{handle}"
        return url

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup | Tag:
        """Extract only the <main> element and remove any featured collection section."""
        main = soup.find("main")
        if main:
            for sec in main.select('section[id*="featured_collection"]'):
                sec.decompose()
            return main
        return soup
