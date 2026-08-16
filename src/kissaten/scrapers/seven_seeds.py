"""Seven Seeds scraper implementation with Shopify JSON extraction.

Seven Seeds (sevenseeds.com.au) is a Melbourne-based specialty coffee roaster
founded in 2007. The store is Shopify-hosted; the curated ``coffee``
collection is the site's canonical "All Coffee" page and contains exactly the
currently-available whole-bean coffees (single origins, house blends and the
decaf), so filtering on ``product_type == "Coffee"`` within it yields only
beans.

Product URLs are canonicalised to the no-collection form used by the live
site (``/products/<handle>``). The product pages carry the flavour descriptors
(profile / with notes of / roast) that the Shopify JSON body_html omits for the
Shogun-built house blends, so product pages are scraped with a ``preprocess
_product_soup`` prune to keep token usage low.
"""

import logging

from bs4 import BeautifulSoup

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="seven-seeds",
    display_name="Seven Seeds",
    roaster_name="Seven Seeds",
    website="https://sevenseeds.com.au",
    description="Melbourne-based specialty coffee roaster founded in 2007, "
    "known for its flagship Carlton roastery and cafe, single origin coffees "
    "and house blends",
    requires_api_key=True,
    currency="AUD",
    country="Australia",
    status="available",
)
class SevenSeedsScraper(ShopifyJsonScraper):
    """Scraper for Seven Seeds (sevenseeds.com.au) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Seven Seeds scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Seven Seeds",
            base_url="https://sevenseeds.com.au",
            products_json_urls=[
                "https://sevenseeds.com.au/collections/coffee/products.json",
            ],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude non-coffee products (subscriptions, gift cards, equipment,
        # merch, etc.) as a defensive net on top of the product_type filter.
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
            "capsules",
            "pods",
            "cold-brew-cans",
            "easy-pour",
            "drip-bags",
            "cold-filter-cask",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Seven Seeds product URLs.

        Seven Seeds' canonical/live product pages are the no-collection form
        ``/products/<handle>`` (confirmed via the page's ``rel=canonical``), so
        strip the ``/collections/<slug>`` segment that the products.json base
        URL injects.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs, keeping only whole-bean coffee.

        The default base-class filter (``is_coffee_product_url`` +
        ``is_coffee_product_name``) is intentionally conservative and would pass
        the collection's drip-bag and cold-coffee-cask items (their handles
        don't trip an exclude keyword). Since the curated ``coffee`` collection
        mixes beans with a couple of non-bean items, filter explicitly on the
        Shopify ``product_type == "Coffee"`` before building the URL.
        """
        products = await self._fetch_all_shopify_products(store_url)
        found_urls = []

        for product in products:
            handle = product.get("handle")
            if not handle:
                continue

            # Only accept products Shopify itself classifies as coffee.
            if product.get("product_type", "") != "Coffee":
                logger.debug(f"Skipping non-coffee product type: {handle} ({product.get('product_type')})")
                continue

            # Skip explicitly excluded product slugs (matches if slug is a substring of handle).
            if any(slug in handle for slug in self.exclude_slugs):
                logger.debug(f"Skipping excluded product slug: {handle}")
                continue

            # Build product URL using the base of the products.json URL.
            base_path = store_url.replace("/products.json", "")
            url = f"{base_path}/products/{handle}"

            # Preprocess the URL (e.g. to remove collection segments).
            url = self.preprocess_product_url(url)

            # Store metadata for later enrichment and stock status.
            self._shopify_product_data[url] = product

            # A product is in stock if any of its variants are available.
            is_available = any(v.get("available", False) for v in product.get("variants", []))
            self._shopify_stock_status[url] = is_available

            # Filter out non-coffee products using base class logic.
            if self.is_coffee_product_url(url) and self.is_coffee_product_name(product.get("title", "")):
                found_urls.append(url)

        # Dedup on the canonical/formatted URLs (post-preprocess) so the returned
        # list is unique even before the base discover_all_product_urls dedups.
        return self.deduplicate_urls(found_urls)

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Filter the product page HTML down to the bean detail sections.

        Seven Seeds hides the flavour descriptors and sourcing details in static
        content blocks (``div.product__content``, ``section.index-rte-columns``
        and ``div.hero__rte``), so we keep only those to give the AI the bean
        information without extraneous page chrome (header, footer, related
        products, accordions holding generic roast/shipping copy).

        We build a new minimal soup WITH a body: ShopifyJsonScraper injects the
        Shopify JSON context (name/price/variants) at the top of ``soup.body``
        AFTER this hook returns, so keeping a valid body preserves that data.
        """
        blocks = (
            soup.select("div.product__content")
            + soup.select("section.index-rte-columns")
            + soup.select("div.hero__rte")
        )
        if not blocks:
            return soup

        minimal = BeautifulSoup("<html><head></head><body></body></html>", "html.parser")
        for block in blocks:
            minimal.body.append(block)
        return minimal
