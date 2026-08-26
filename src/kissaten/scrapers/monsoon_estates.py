"""Monsoon Estates scraper implementation with Shopify JSON extraction.

Monsoon Estates (monsoonestates.co.uk) is a UK whole-bean roaster selling
coffee alongside training courses and gift subscriptions.

Quirk (documented, do not "fix"): the store consistently misspells "Swiss
Water Decaf" (should be "Swiss Water") in its product titles/handles
(``swiss-water-decaf``, ``swiss-water-decaf-peruvian``). We scrape these
faithfully as-is; the misspelling is intentional site content, not a data
error to correct here.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="monsoon-estates",
    display_name="Monsoon Estates",
    roaster_name="Monsoon Estates",
    website="https://monsoonestates.co.uk",
    description="UK whole-bean coffee roaster (Monsoon Estates Coffee Company) "
    "offering single-origin coffees and blends alongside training courses.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class MonsoonEstatesScraper(ShopifyJsonScraper):
    """Scraper for Monsoon Estates (monsoonestates.co.uk) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Monsoon Estates scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Monsoon Estates",
            base_url="https://monsoonestates.co.uk",
            products_json_urls=["https://monsoonestates.co.uk/products.json"],
            scrape_product_pages=False,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Pin the home-market currency. The products.json payload carries no
        # currency field (null), and Shopify Markets can serve converted prices
        # to the datacenter IP of the HTTP client, so force GBP and mark it as
        # already-detected so the geo-detected value can't override it.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Exclude non-coffee products. The 4 training courses (coffee-experience,
        # latte-art, home-barista, professional-barista-training) and the gift
        # card all carry an empty product_type, so the type=="Coffee" filter in
        # _extract_product_urls_from_store drops them automatically. The two
        # gift-subscription products are typed "Coffee" but are subscriptions, so
        # we exclude them here by handle. Training slugs are listed as a safety
        # net in case Shopify ever assigns them a Coffee type.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "training",
            "coffee-experience",
            "latte-art",
            "home-barista",
            "professional-barista-training",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "mug",
            "tumbler",
            "hoodie",
            "tshirt",
            "capsules",
            "pods",
            "easy-pour",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Monsoon Estates product URLs.

        The site's canonical/live product pages are the no-collection form
        ``/products/<handle>``, so strip the ``/collections/<slug>`` segment
        that the products.json base URL injects.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs, keeping only whole-bean coffee.

        Filtering on the Shopify ``product_type == "Coffee"`` is the cleanest
        route here: it selects exactly the whole-bean catalogue (the training
        courses and gift card carry an empty product_type and are dropped),
        while the two gift subscriptions are excluded below by slug.
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
