"""Bell's Beans scraper implementation with Shopify JSON extraction.

Bell's Beans (bellsbeans.co.uk, Surrey) is a Shopify store. The curated
``coffee`` collection is empty on the live site, so the whole catalogue is
fetched from the root ``products.json`` and filtered to genuine coffee.

IMPORTANT (tasting-kit policy): this store sells sampler/taster packs
(``sample-eeny``, ``sample-meeny``, ``sample-pack-moe``, ``sample-miny``,
``sample-pack-natty``). Those are NOT excluded - they flow through the
pipeline, get flagged ``is_tasting_kit = true`` / ``requires_review = true``
by the base ``_apply_product_flags`` and land in the admin review queue. Only
genuine non-coffee products (``gift-membership``, ``the-coffee-club-subscription``)
are excluded.

Canonical product URLs are the no-collection form ``/products/<handle>``,
which the root products.json base URL already produces.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="bells-beans",
    display_name="Bell's Beans",
    roaster_name="Bell's Beans",
    website="https://bellsbeans.co.uk",
    description="Specialty coffee roaster based in Woking, Surrey (UK). "
    "Sells single-origin coffees, house blends, decaf and curated sample "
    "packs through a Shopify store.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class BellsBeansScraper(ShopifyJsonScraper):
    """Scraper for Bell's Beans (bellsbeans.co.uk) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Bell's Beans scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Bell's Beans",
            base_url="https://bellsbeans.co.uk",
            products_json_urls=["https://bellsbeans.co.uk/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Exclude only genuine non-coffee products (subscriptions / gifts).
        # Deliberately NOT excluded: sample packs (sample-eeny, sample-meeny,
        # sample-pack-moe, sample-miny, sample-pack-natty) - those are curated
        # tasting kits, flagged for review instead of dropped.
        self.exclude_slugs = [
            "gift-subscription",
            "gift-membership",
            "the-coffee-club-subscription",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "mug",
            "tumbler",
            "hoodie",
            "tshirt",
            "apparel",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

        # Store serves GBP natively; pin defensively.
        self.store_currency = "GBP"
        self._currency_detected = True

    def _get_tasting_kit_url_patterns(self) -> list[str]:
        """Add Bell's sampler URL tokens to the base kit patterns.

        The base patterns match ``sample-pack-*`` but not Bell's other
        sampler handles (``sample-eeny``, ``sample-meeny``, ``sample-miny``),
        so extend with the store's ``sample-`` predecessors.
        """
        return super()._get_tasting_kit_url_patterns() + ["sample"]

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Bell's product URLs.

        Bell's canonical/live product pages are the no-collection form
        ``/products/<slug>``. The root products.json base already yields that
        form; this is a defensive normalization if a collection URL ever
        appears.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from the full catalogue.

        The catalogue mixes coffee with two genuine non-coffee entries
        (gift-membership, the-coffee-club-subscription) - excluded via
        ``exclude_slugs``. Sampler packs are INSTRUCTED to flow through: they
        are kept by the base URL/name filters and flagged for review later.
        """
        products = await self._fetch_all_shopify_products(store_url)
        found_urls = []

        for product in products:
            handle = product.get("handle")
            if not handle:
                continue

            # Skip explicitly excluded non-coffee slugs.
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

            # Filter out non-coffee products using base class logic
            # (sample-pack products pass through this - they are later
            #  flagged is_tasting_kit by _apply_product_flags).
            if self.is_coffee_product_url(url) and self.is_coffee_product_name(product.get("title", "")):
                found_urls.append(url)

        # Dedup on the canonical/formatted URLs.
        return self.deduplicate_urls(found_urls)

    def _extract_currency_from_html(self, soup) -> str:
        """Pin the store currency to GBP."""
        return "GBP"

    def postprocess_extracted_bean(self, bean):
        """Force the bean currency to GBP (store base currency)."""
        bean = super().postprocess_extracted_bean(bean)
        bean.currency = "GBP"
        return bean
