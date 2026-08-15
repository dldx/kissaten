"""Kurasu scraper implementation with Shopify JSON extraction."""

import logging

from bs4 import BeautifulSoup

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="kurasu",
    display_name="Kurasu",
    roaster_name="Kurasu",
    website="https://kurasu.kyoto",
    description="Kyoto-based Japanese coffee roaster and shop known for carefully sourced "
    "single origin and seasonal blend coffees, roasted in-house.",
    requires_api_key=True,
    currency="USD",
    country="Japan",
    status="available",
)
class KurasuScraper(ShopifyJsonScraper):
    """Scraper for Kurasu (kurasu.kyoto) using the Shopify products.json endpoint."""

    def __init__(self, api_key: str | None = None):
        """Initialize the Kurasu scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Kurasu",
            base_url="https://kurasu.kyoto",
            products_json_urls=["https://kurasu.kyoto/collections/coffee/products.json"],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

        # Exclude non-whole-bean products that appear in the coffee collection:
        # drip bags (single-serve ground coffee), capsules, and subscriptions.
        self.exclude_slugs = [
            "subscription",
            "capsule",
            "drip-coffee-bag",
            "drip-bag",
        ]

    def preprocess_product_url(self, url: str) -> str:
        """Ensure product URLs use the canonical /products/<handle> form.

        ShopifyJsonScraper builds collection paths (e.g.
        /collections/coffee/products/<handle>) from the products.json base, but
        Kurasu's real product pages are just /products/<handle>, so we strip the
        collection segment to keep the URLs aligned with the live site.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1]
            return f"{self.base_url}/products/{handle}"
        return url

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Prune the product page down to the coffee details for token efficiency.

        Kurasu embeds a structured "Coffee Profile" table (roast level, country,
        region, altitude, variety, process, flavor note) in
        ``div[class*="ai-metafield-table-container"]`` and a "Roaster's Comment"
        prose block in ``div.rich-content``. Keep only those plus a valid body so
        ShopifyJsonScraper can still inject the product JSON (name/price/variants)
        at the top of the body for the AI.
        """
        blocks = soup.select('div[class*="ai-metafield-table-container"]') + soup.select("div.rich-content")
        if not blocks:
            return soup

        minimal = BeautifulSoup("<html><head></head><body></body></html>", "html.parser")
        for block in blocks:
            minimal.body.append(block)
        return minimal

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract coffee product URLs, skipping fully-sold-out products.

        Mirrors ``ShopifyJsonScraper._extract_product_urls_from_store`` but skips
        products where every variant is unavailable, so we do not waste AI tokens
        scraping pages that can only be marked out-of-stock. Stock status is still
        recorded so diffjson stock updates work correctly.
        """
        products = await self._fetch_all_shopify_products(store_url)
        found_urls = []

        for product in products:
            handle = product.get("handle")
            if not handle:
                continue

            if any(slug in handle for slug in self.exclude_slugs):
                logger.debug(f"Skipping excluded product slug: {handle}")
                continue

            base_path = store_url.replace("/products.json", "")
            url = f"{base_path}/products/{handle}"
            url = self.preprocess_product_url(url)

            self._shopify_product_data[url] = product

            is_available = any(v.get("available", False) for v in product.get("variants", []))
            self._shopify_stock_status[url] = is_available

            # Sold-out filtering: record stock status, but don't scrape pages for
            # products that have no available variant this session.
            if not is_available:
                logger.debug(f"Skipping sold-out product: {handle}")
                continue

            if self.is_coffee_product_url(url) and self.is_coffee_product_name(product.get("title", "")):
                found_urls.append(url)

        return found_urls
