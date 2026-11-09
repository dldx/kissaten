"""GWO Coffee scraper implementation with Shopify JSON extraction.

GWO (gwo.coffee) is a one-person micro-roastery in Eindhoven that releases
light-roast single origins as periodic themed drops instead of a standing
shelf. The store is plain Shopify, so everything is read from ``products.json``.

Two things make this store unusual and shape the scraper:

* **The store is currently empty on purpose.** The roaster is retiring a Roest
  L100 and moving onto a Roest P3000, so the shop is closed until the machine
  is installed and the crowdfunding rewards are shipped out; the first P3000
  drop is scheduled for 25 October 2026. In the meantime ``products.json``
  holds exactly one non-coffee placeholder product (``p3000-drops-loading``,
  a 0.00 EUR announcement page) and all 14 real coffees sit in Past Releases,
  sold out. The scraper is written to survive the store repopulating without
  any code change: the only slug-level exclusion is the placeholder, and
  out-of-stock diffjson updates are left to the base class so a failed listing
  fetch is never mistaken for a delisted catalogue.
* **``product_type`` is empty on every product**, so product_type filtering is
  impossible. Beans are instead selected by handle/title through the base-class
  URL/name heuristics, with an explicit slug exclusion list for the handful of
  things that are not beans.

Tasting sets (``gv-oma-tasting-set``, ``that-v3``) are deliberately *not*
excluded: they are coffee for sale and are meant to flow through so
``_apply_product_flags`` can mark them ``is_tasting_kit`` / ``requires_review``
and land them in the admin review queue instead of being silently dropped.
"""

import logging

from ..schemas import CoffeeBean
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="gwo-coffee",
    display_name="GWO Coffee",
    roaster_name="GWO Coffee",
    website="https://gwo.coffee",
    description="Eindhoven micro-roastery and one-person operation releasing light-roast single origins "
    "as periodic themed drops, now moving from a Roest L100 to a P3000.",
    requires_api_key=True,
    currency="EUR",
    country="Netherlands",
    status="experimental",
)
class GwoCoffeeScraper(ShopifyJsonScraper):
    """Scraper for GWO Coffee (gwo.coffee) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize GWO Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="GWO Coffee",
            base_url="https://gwo.coffee",
            products_json_urls=["https://gwo.coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Pin the home-market currency: Shopify Markets can serve geo-converted
        # prices depending on caller IP / Accept-Language, so runtime detection
        # is not trusted.
        self.store_currency = "EUR"
        self._currency_detected = True

        # product_type is empty across the whole catalogue, so beans are picked
        # by handle/title instead (see _extract_product_urls_from_store) and
        # only non-bean handles need to be excluded explicitly.
        self.exclude_slugs = [
            # Store-closure announcement for the L100 -> P3000 roaster swap:
            # a 0.00 EUR "big roaster drops loading..." page, not a bean. It is
            # the only product in the catalogue right now and disappears as soon
            # as the P3000 drops open for sale.
            "p3000-drops-loading",
            # NOTE: tasting sets (gv-oma-tasting-set, that-v3) are deliberately
            # NOT excluded — they are coffee for sale and get
            # is_tasting_kit/requires_review flagging downstream.
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Force the bean currency to EUR regardless of what was extracted."""
        bean.currency = "EUR"
        return super().postprocess_extracted_bean(bean)

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs, filtering out the non-bean placeholder.

        ``product_type`` is empty on every GWO product, so there is no
        product_type whitelist to apply the way 19grams does. Instead the
        placeholder/announcement handle is excluded by slug and the base-class
        URL and product-name heuristics do the rest.
        """
        products = await self._fetch_all_shopify_products(store_url)
        found_urls = []

        for product in products:
            handle = product.get("handle")
            if not handle:
                continue

            # Skip explicitly excluded product slugs (matches if slug is a substring of handle).
            if any(slug in handle for slug in self.exclude_slugs):
                logger.debug(f"Skipping excluded product slug: {handle}")
                continue

            # Build product URL using the base of the products.json URL.
            base_path = store_url.replace("/products.json", "")
            url = f"{base_path}/products/{handle}"

            # Canonicalize to the site's real /products/<handle> form.
            url = self.preprocess_product_url(url)

            # Store metadata for later enrichment and stock status.
            self._shopify_product_data[url] = product

            # A product is in stock if any of its variants are available.
            is_available = any(v.get("available", False) for v in product.get("variants", []))
            self._shopify_stock_status[url] = is_available

            # Filter out non-coffee products using base class logic.
            if self.is_coffee_product_url(url) and self.is_coffee_product_name(product.get("title", "")):
                found_urls.append(url)

        return found_urls
