"""Parallel Coffee scraper implementation with Shopify JSON extraction.

Parallel Coffee (parallelcoffee.co.uk -> www.parallelcoffee.co.uk) is a UK
specialty coffee roaster on Shopify. The site nav curates a dedicated
whole-bean collection, ``coffee-beans``, whose ``products.json`` returns 15
published products all typed ``Coffee`` (verified live, 2026-08) and no
equipment/accessories/grinders. The scraper uses that curated collection rather
than ``collections/all`` (which mixes in ``bundles``, ``filter-brewing`` and
``coffee accessory`` / ``Coffee Grinder`` / equipment types across the 61-item
catalogue).

Because the collection is already coffee-only, the ``product_type == "Coffee"``
filter in ``_extract_product_urls_from_store`` is a defensive guard: it encodes
the "whole-bean only, no equipment" requirement even if the collection's
contents change, and ``exclude_slugs`` drops any grinder/accessory/equipment
product that ever leaks in.

The Shopify ``body_html`` is **empty** for these products (and the JSON-LD
``description`` is also empty), so the bean details (origin, farm, region,
variety, process, altitude, tasting notes, importer notes, roasting analytics,
farmer notes) live only in the rendered product page's static HTML inside the
``product_top-info_layout`` Webflow container. JSON-only scraping is therefore
not viable; the scraper uses ``scrape_product_pages=True`` with
``use_optimized_mode=False`` and prunes the page to that container via
``preprocess_product_soup`` to keep AI token cost down. The injected Shopify
JSON still supplies the name, price, variants and stock status.

Canonical product URLs are the no-collection form ``/products/<handle>``
(confirmed via the JSON-LD ``offer.url`` / ``BreadcrumbList`` ``@id``), so the
collection segment that each products.json base URL injects is stripped in
``preprocess_product_url``.

The store is a UK/GBP shop. Shopify may expose a ``priceCurrency: EUR`` field
in JSON-LD, but that is a quirk; prices display in GBP and the roaster is based
in the UK, so the home currency is pinned to GBP.
"""

import logging

from bs4 import BeautifulSoup

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="parallel",
    display_name="Parallel",
    roaster_name="parallel",
    website="https://www.parallelcoffee.co.uk",
    description="UK specialty coffee roaster curating a dedicated whole-bean "
    "collection of single-origin coffees and signature espresso blends, with "
    "an emphasis on direct farm relationships and transparent sourcing.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class ParallelCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Parallel Coffee (parallelcoffee.co.uk) using Shopify products.json.

    Uses the roaster's own curated ``coffee-beans`` collection rather than
    ``collections/all``, which also mixes in bundles, filter-brewing and
    accessory/grinder/equipment products. The curated endpoint returns ~15
    Coffee-typed whole-beans and no equipment.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Parallel Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="parallel",
            base_url="https://www.parallelcoffee.co.uk",
            products_json_urls=[
                "https://www.parallelcoffee.co.uk/collections/coffee-beans/products.json",
            ],
            scrape_product_pages=True,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Parallel is a UK store priced in GBP. Although Shopify's JSON-LD can
        # carry a "priceCurrency": "EUR" marker, prices render in £; pin the
        # home currency and mark it as detected to skip the collection-page
        # currency-detection path.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Exclude genuine non-coffee products only. Do NOT exclude sampler /
        # taster-pack / selection slugs here: the base class flags tasting kits
        # (flag-don't-exclude) so they land in the admin review queue rather
        # than being dropped.
        self.exclude_slugs = [
            "grinder",
            "accessory",
            "equipment",
            "filter-brewing",
            "v60",
            "chemex",
            "kettle",
            "dripper",
            "brewer",
            "mug",
            "tumbler",
            "subscription",
            "gift-card",
            "giftcard",
            "wholesale",
            "merchandise",
            "merch",
            "apparel",
            "tshirt",
            "pods",
            "capsules",
            "cold-brew-cans",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Parallel Coffee product URLs.

        The live site canonizes product pages to the no-collection form
        ``/products/<handle>`` (confirmed via the JSON-LD ``offer.url`` and
        ``BreadcrumbList`` ``@id``), so strip the ``/collections/<slug>`` segment
        that the products.json base URL injects.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs, keeping only whole-bean coffee.

        The curated ``coffee-beans`` collection already returns only
        ``product_type == "Coffee"`` products, but filter on that type explicitly
        anyway so the whole-bean-only requirement holds even if the collection's
        contents change (or a product_type is mis-tagged). ``exclude_slugs``
        drops any grinder/accessory/equipment product that slips through.
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

    def preprocess_product_soup(self, soup):
        """Prune the product page to the spec's bean-information section.

        Parallel's Shopify ``body_html`` is empty, so the AI must read the
        rendered product page. The bean's fields (origin/farm/region/variety/
        process/altitude/notes plus importer, roasting and farmer notes) all live
        inside the ``product_top-info_layout`` Webflow container. Keeping only
        that container trims the ~170KB page to the relevant tokens; the injected
        Shopify JSON still supplies the title, price and variants.
        """
        top_info = soup.find("div", class_="product_top-info_layout")
        if top_info is not None:
            container = top_info.parent
            if container is not None:
                return BeautifulSoup(str(container), "lxml")
        return soup
