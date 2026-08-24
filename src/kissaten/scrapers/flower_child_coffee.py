"""Flower Child Coffee scraper implementation with Shopify JSON extraction."""

import logging
import re

from bs4 import BeautifulSoup

from ..schemas import CoffeeBean
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="flower-child-coffee",
    display_name="Flower Child Coffee",
    roaster_name="Flower Child Coffee",
    website="https://flowerchildcoffee.com",
    description="Coffee roaster based in Oakland, California focused on clean, vibrant cups.",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="available",
)
class FlowerChildCoffeeScraper(ShopifyJsonScraper):
    """Scraper using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Flower Child Coffee",
            base_url="https://flowerchildcoffee.com",
            # Only the active catalogue is scraped. The `archive` collection is
            # deliberately excluded (kept commented, like Sey's archived-coffees
            # collection) because it is a historical/out-of-stock catalogue that
            # would inflate the active bean count and drag down the in-stock
            # ratio. Any archived bean is marked out of stock (see
            # _extract_bean_with_ai below / via Shopify variant availability).
            products_json_urls=[
                "https://flowerchildcoffee.com/collections/active-coffee/products.json",
                # "https://flowerchildcoffee.com/collections/archive/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )
        # Exclude subscription products or other non-coffee items
        self.exclude_slugs = ["subscription", "drip-bag", "mystery-coffee", "bundle", "pods", "cascara", "gift-card"]

    def _canonicalize_url(self, url: str) -> str:
        # Canonical product pages are /products/<handle>; collapse the collection
        # segment so old /collections/<slug>/products/<handle> history entries match
        # the new canonical form (prevents re-scrape / false out-of-stock).
        return re.sub(r"/collections/[^/]+/products/", "/products/", url)

    def preprocess_product_url(self, url: str) -> str:
        """Canonicalize collection-prefixed product URLs to ``/products/<handle>``.

        A product listed in multiple collections is the same physical product,
        so collapsing the collection segment merges the same handle across
        collections (e.g. active-coffee + archive) without merging distinct
        filter/espresso products (those keep different handles).
        """
        return self._canonicalize_url(url)

    async def _extract_bean_with_ai(
        self,
        ai_extractor,
        soup: BeautifulSoup,
        product_url: str,
        use_optimized_mode: bool = False,
        translate_to_english: bool = False,
    ) -> CoffeeBean | None:
        """Extract a bean, marking archived products (all variants unavailable) as out of stock."""
        bean = await super()._extract_bean_with_ai(
            ai_extractor,
            soup,
            product_url,
            use_optimized_mode=use_optimized_mode,
            translate_to_english=translate_to_english,
        )
        if bean is not None:
            # Archived products (Shopify variants all unavailable) are out of stock.
            # With the archive collection commented out this is defensive, but it
            # mirrors Sey's archive handling and keeps any archived bean correctly
            # flagged even if the archive source is ever re-enabled.
            in_stock = self._shopify_stock_status.get(product_url, True)
            if not in_stock:
                bean.in_stock = False
                logger.info(f"Marked {product_url} as out of stock (archived)")
        return bean
