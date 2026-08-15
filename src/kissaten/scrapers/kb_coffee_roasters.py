"""KB Coffee Roasters scraper.

French specialty coffee roaster and café based in Paris (rue des Martyrs /
avenue Tudaine, between Pigalle and Montmartre), offering single origin
coffees and espresso, whole bean and a range of grind options. The store is
hosted on Shopify and, being in French, the extracted data is translated to
English.
"""

import logging

from ..schemas import CoffeeBean
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="kb-coffee-roasters",
    display_name="KB",
    roaster_name="KB",
    website="https://kbcoffeeroasters.com",
    description="French specialty coffee roaster and café based in Paris, "
    "offering single origin coffees and espresso, whole bean and ground",
    requires_api_key=True,  # Using AI extraction for best results
    currency="EUR",
    country="France",
    status="available",
)
class KBCoffeeRoastersScraper(ShopifyJsonScraper):
    """Scraper for KB Coffee Roasters (kbcoffeeroasters.com)."""

    def __init__(self, api_key: str | None = None):
        """Initialize the scraper.

        Args:
            api_key: Optional API key for AI-powered extraction
        """
        super().__init__(
            roaster_name="KB",
            base_url="https://kbcoffeeroasters.com",
            # The store keeps its retail coffee untagged into a single curated
            # collection, so the whole catalog is fetched and beans are selected
            # by the "Coffee" tag in _extract_product_urls_from_store.
            products_json_urls=["https://kbcoffeeroasters.com/collections/all/products.json"],
            use_optimized_mode=True,
            rate_limit_delay=1.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # The site is a French (EUR) store; currency detection from the page
        # meta tags is unreliable here (the collection page can surface a
        # non-EUR market currency), so pin EUR explicitly and skip detection.
        self.store_currency = "EUR"
        self._currency_detected = True

        # Defense-in-depth on top of the "Coffee" tag filter: drop the monthly
        # subscription product and other known non-bean items that carry a
        # coffee-ish tag or name.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "carte-cadeau",
            "cascara",  # coffee cherry tea, not beans
        ]

        # Initialize AI extractor (recommended for complex Shopify sites)
        self.ai_extractor = None
        try:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
        except ImportError:
            logger.warning("AI extractor not available - falling back to traditional extraction")

    def preprocess_product_url(self, url: str) -> str:
        """Standardize the product URL to the canonical no-collection form.

        ShopifyJsonScraper builds URLs from the products.json URL base, yielding
        https://kbcoffeeroasters.com/collections/all/products/<handle>, but the
        site's real/canonical product pages are https://kbcoffeeroasters.com/products/<handle>.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1]
            return f"{self.base_url}/products/{handle}"

        return url

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract coffee product URLs, selecting only beans by their tag.

        Every retail coffee bean on this store carries a "Coffee" tag, while
        books/equipment/merch/gifts do not, so the tag is a precise selector
        and avoids a long brittle exclude list. The underlying stock-status and
        product-data maps are still populated (as in the base implementation)
        so diffJSON stock updates keep working.
        """
        products = await self._fetch_all_shopify_products(store_url)
        found_urls = []

        for product in products:
            handle = product.get("handle")
            if not handle:
                continue

            tags = {t.lower() for t in product.get("tags", [])}
            if "coffee" not in tags:
                logger.debug(f"Skipping non-coffee tagged product: {handle}")
                continue

            url = f"{store_url.replace('/products.json', '')}/products/{handle}"
            url = self.preprocess_product_url(url)

            # Store metadata for later enrichment and stock status
            self._shopify_product_data[url] = product

            # A product is in stock if any of its variants are available
            is_available = any(v.get("available", False) for v in product.get("variants", []))
            self._shopify_stock_status[url] = is_available

            # Skip explicitly excluded product slugs (substring match)
            if any(slug in handle for slug in self.exclude_slugs):
                logger.debug(f"Skipping excluded product slug: {handle}")
                continue

            if self.is_coffee_product_url(url) and self.is_coffee_product_name(product.get("title", "")):
                found_urls.append(url)

        return found_urls

    async def _scrape_new_products(self, product_urls: list[str], use_optimized_mode: bool = False) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction.

        Args:
            product_urls: List of URLs for new products
            use_optimized_mode: Whether to use optimized Shopify extraction mode

        Returns:
            List of newly scraped CoffeeBean objects
        """
        if not product_urls:
            return []

        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=False,
            translate_to_english=True,  # The site is in French
            use_optimized_mode=use_optimized_mode or self.use_optimized_mode,
        )
