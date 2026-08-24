"""Asylum Coffeehouse scraper implementation with Shopify JSON extraction.

Asylum Coffeehouse (www.asylumcoffeehouse.com) is a Singapore specialty coffee
shop (Instagram @asylumcoffeesg). Its Shopify storefront presents in SGD and
sells Colombian filter coffees (Yellow Sudan Rume, Pink Bourbon, Caturra
Natural, Castillo Honey, plus a Sunrise Decaf), a Peru Washed Gesha, the house
**Keluak** espresso blend, and April brewing gear (April Plastic Brewer, April
filter papers) plus an Asylum Bloom Cup (A.B.C.) merch cup.

The site curates two coffee collections that together isolate the whole-bean
lineup from the gear/merch:

- ``/collections/filter-roast``: the filter coffees + the April filter papers
  and the subscription plan (non-coffee)
- ``/collections/espresso-roast``: the Keluak espresso blend

Filtering on ``product_type == "Specialty Coffee"`` inside the curated
collections keeps only beans; the gear/merch either live outside these
collections or carry a different product type. The ``body_html`` of every
coffee product is rich (varietal, farm, altitude, tasting notes, processing
notes, cupping score), so a JSON-only scrape with
``use_optimized_mode=True`` is sufficient — no page scraping needed.

Product URLs are canonicalised to the no-collection form (``/products/<handle>``)
used by the live site.
"""

import logging

from ..schemas import CoffeeBean
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="asylum-coffeehouse",
    display_name="Asylum Coffeehouse",
    roaster_name="Asylum Coffeehouse",
    website="https://www.asylumcoffeehouse.com",
    description="Singapore specialty coffee shop selling Colombian and Peruvian "
    "filter coffees, the Keluak espresso blend and April brewing gear via a "
    "Shopify storefront presented in SGD.",
    requires_api_key=True,
    currency="SGD",
    country="Singapore",
    status="available",
)
class AsylumCoffeehouseScraper(ShopifyJsonScraper):
    """Scraper for Asylum Coffeehouse (asylumcoffeehouse.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Asylum Coffeehouse scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Asylum Coffeehouse",
            base_url="https://www.asylumcoffeehouse.com",
            products_json_urls=[
                "https://www.asylumcoffeehouse.com/collections/filter-roast/products.json",
                "https://www.asylumcoffeehouse.com/collections/espresso-roast/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # This store presents exclusively in SGD (Shopify.currency active SGD,
        # verified from the served HTML). Pin the currency so an IP/locale
        # based market conversion can never override it.
        self.store_currency = "SGD"
        self._currency_detected = True

        # Defensive net on top of the product_type filter (the Bloom Cup merch
        # and the subscription would otherwise be candidate products).
        self.exclude_slugs = [
            "bloom-cup",
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "brewing",
            "accessory",
            "merch",
            "merchandise",
            "capsules",
            "pods",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Asylum Coffeehouse product URLs.

        The live site's canonical product pages are ``/products/<handle>``
        (no collection segment), so strip the ``/collections/<slug>`` segment
        that the products.json URL base injects.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs, keeping only whole-bean coffee.

        The curated ``filter-roast`` + ``espresso-roast`` collections still mix
        in the April filter papers (``Drip Coffee Brewer``) and the filter
        subscription (empty product type), so filter explicitly on Shopify's
        ``product_type == "Specialty Coffee"`` before building the URL. This
        drops the gear and subscription entries while keeping all six filter
        coffees (incl. the Peru Washed Gesha) and the Keluak espresso blend.
        """
        products = await self._fetch_all_shopify_products(store_url)
        found_urls = []

        for product in products:
            handle = product.get("handle")
            if not handle:
                continue

            # Only accept products Shopify itself classifies as specialty coffee.
            if product.get("product_type", "") != "Specialty Coffee":
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

        # Dedup on the canonical/formatted URLs (post-preprocess) in case the
        # collections overlap.
        return self.deduplicate_urls(found_urls)

    def postprocess_extracted_bean(self, bean) -> CoffeeBean | None:
        """Pin the bean currency to SGD and backfill a missing price.

        The store presents exclusively in SGD, so ``bean.currency`` is pinned
        as a guard against any geo-detected market conversion. When the AI
        leaves ``bean.price`` empty, fall back to the authoritative Shopify
        variant price (cheapest variant, matching how ``price_options``
        usually captures the per-weight options).
        """
        bean = super().postprocess_extracted_bean(bean)
        if bean is None:
            return None
        bean.currency = "SGD"
        if bean.price is None:
            product_data = self._shopify_product_data.get(str(bean.url))
            if product_data:
                prices = [
                    float(v["price"])
                    for v in product_data.get("variants", [])
                    if v.get("price") is not None
                ]
                if prices:
                    bean.price = min(prices)
                    logger.info(f"Backfilled missing price for {bean.url} from Shopify variants: {bean.price}")
        return bean
