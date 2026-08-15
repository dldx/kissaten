"""Cat & Cloud scraper implementation with Shopify JSON extraction."""

import logging

from bs4 import BeautifulSoup

from ..schemas import CoffeeBean
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="cat-and-cloud",
    display_name="Cat & Cloud",
    roaster_name="Cat & Cloud",
    website="https://catandcloud.com",
    description="Santa Cruz, California specialty coffee company focused on transparency, "
    "approachable specialty coffee, and a fun-roasting atmosphere.",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="available",
)
class CatAndCloudScraper(ShopifyJsonScraper):
    """Scraper for Cat & Cloud (catandcloud.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Cat & Cloud scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Cat & Cloud",
            base_url="https://catandcloud.com",
            products_json_urls=["https://catandcloud.com/collections/coffee/products.json"],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # The coffee collection still mixes in merchant/gift/subscription items.
        # Exclude non-bean products (subscriptions, gift cards, instant coffee, merch).
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "merch",
            "apparel",
            "mug",
            "tumbler",
            "hoodie",
            "tshirt",
            "tee",
            "keychain",
            "hat",
            "pin",
            "bandana",
            "tote",
            "sticker",
            "spoon",
            "swift-coffee-6-pack",  # Instant coffee 6 pack (sold out)
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Cat & Cloud product URLs.

        The site's canonical product URL is the no-collection form
        ``https://catandcloud.com/products/<handle>``. Strip the collection
        segment added by ``ShopifyJsonScraper`` so our URLs match the real pages.
        """
        base_path = f"{self.base_url}/products"
        if "/collections/" in url and "/products/" in url:
            handle = url.split("/products/")[-1]
            return f"{base_path}/{handle}"
        return url

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Filter the product page HTML down to the product info container.

        Cat & Cloud keeps the product meta (title, description, price) and the
        bean detail (Origin Info accordion with country/region/producer/variety/
        elevation/process/tasting notes) inside ``div.product__info-container``.
        Keep only that block to give the AI the bean information while avoiding
        page chrome (header/footer/related products) that burns tokens.
        """
        info = soup.select_one("div.product__info-container")
        if info:
            logger.info("Limiting extraction to div.product__info-container")
            return info
        return soup

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Force the correct store currency on extracted beans.

        This store always sells in USD. The base class resolves the default
        currency from the registry by the ``roaster_name`` (which lowercases
        to ``cat & cloud`` and misses the registry key ``cat-and-cloud``),
        falling back to GBP, and this store's signed client can serve a
        GBP-localized storefront variant. Pin currency to USD explicitly,
        applying it after super() so the Shopify base's store-currency
        override does not clobber it.
        """
        bean = super().postprocess_extracted_bean(bean)
        bean.currency = "USD"
        return bean
