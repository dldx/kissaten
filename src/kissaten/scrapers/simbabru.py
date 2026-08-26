"""Simba Bru scraper implementation with Shopify JSON extraction.

Simba Bru (simbabru.co.uk) is a UK specialty coffee roaster roasting single
origins, blends and a decaf in small batches, priced in GBP. The storefront
runs on Shopify and serves a bare 200 from CloudFront without geolocation
blocking.

Feed selection (live probe, 2026-08): ``collections/all`` mixes the coffee
beans with 10 non-coffee products (6 ``Brewing Equipment`` and 4 ``Gifts and
Merch``). The roaster curates four dedicated coffee collections that together
carry every coffee bean:

- ``single-origin-speciality-roasted-coffee-beans`` (5)
- ``decaf-coffee-beans`` (1)
- ``espresso-blends`` (1)
- ``seasonal-roasted-coffee-beans`` (1)

Merging these four ``products.json`` feeds and filtering to coffee product
types yields the 5 unique coffee products (handles like ``finca-la-tuna-peru``,
``planadas-colombia``, ``eagle-monte-carmelo-brazil``, ``el-buho-decaf-colombia``
and ``sutton-road-espresso-blend-brazil-colombia``) — the same set that
``collections/all`` publishes as ``Roasted Coffee Beans``. The equipment/merch
catalogue is sizable, so those collections are excluded here rather than using
``collections/all``.

Product-type filtering is a defensive net alongside the explicit equipment
``exclude_slugs``: any product whose ``product_type`` is neither
``Roasted Coffee Beans`` nor coffee-like (``coffee``) is dropped, which keeps
the sizable brew-equipment catalogue out of the feed even if it ever leaks
into one of the coffee collections.

Samplers/tasting kits are deliberately NOT excluded — the base
``_apply_product_flags`` review pipeline flags any such product
``is_tasting_kit``/``requires_review`` into the admin review queue rather than
dropping it.

The ``body_html`` in the products.json payload is uniformly structured — a
prose tasting-note paragraph plus a producer/farm/origin description — so the
injection-only path is used: ``scrape_product_pages=False`` with
``use_optimized_mode=True`` (the AI extracts from the Shopify JSON context,
the cheapest token option; the rendered product page mirrors the same content
and adds nothing the JSON lacks).

Canonical URLs are the no-collection ``/products/<handle>`` form (confirmed
via ``rel=canonical`` and ``og:url`` on the live product pages), so the
collection segment produced by the products.json base is stripped in
``preprocess_product_url``. Product URLs are keyed/deduped on this canonical
form so products appearing in multiple coffee collections are counted once.

Currency: the store is a UK GBP store, so ``store_currency`` is pinned to
``GBP`` and ``_currency_detected`` to True up front — a geo-detected market
must never overwrite the home prices.
"""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="simbabru",
    display_name="Simba Bru",
    roaster_name="Simba Bru",
    website="https://simbabru.co.uk",
    description="UK specialty coffee roaster roasting single origins, blends "
    "and decaf in small batches — a curated, rotating range of coffee priced "
    "in GBP.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class SimbaBruScraper(ShopifyJsonScraper):
    """Scraper for Simba Bru (simbabru.co.uk) using Shopify products.json.

    Uses the roaster's four dedicated coffee collections rather than
    ``collections/all``, which mixes in 10 brewing-equipment and merch
    products.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Simba Bru scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Simba Bru",
            base_url="https://simbabru.co.uk",
            products_json_urls=[
                "https://simbabru.co.uk/collections/single-origin-speciality-roasted-coffee-beans/products.json",
                "https://simbabru.co.uk/collections/decaf-coffee-beans/products.json",
                "https://simbabru.co.uk/collections/espresso-blends/products.json",
                "https://simbabru.co.uk/collections/seasonal-roasted-coffee-beans/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Simba Bru is a UK store priced in GBP. Pin the home currency and
        # mark it as detected so the collection-page currency-detection path
        # can never overwrite it with a geo-located market price.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Genuine coffee product types (compared lowercased). Anything else
        # (e.g. Brewing Equipment, Gifts and Merch) is dropped before the AI
        # stage. "coffee" catches looser product_type labels like "Single
        # origin, filter" should the catalog ever use them.
        self.coffee_product_types = ("roasted coffee beans", "coffee")

        # Exclude genuine non-coffee products only. The four coffee
        # collections should only ever contain beans, but a defensive
        # equipment/merch list keeps any leaked brew gear out. Deliberately
        # NOT excluded: sampler / taster-pack / gift-box slugs — the base
        # class flags tasting kits (flag-don't-exclude) so they land in the
        # admin review queue rather than being dropped.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "giftcard",
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
            "capsules",
            "pods",
            "cold-brew-cans",
            "grinder",
            "v60",
            "aeropress",
            "chemex",
            "french-press",
            "kettle",
            "scale",
            "brewer",
            "filter",
            "dripper",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Override to filter coffee products by product_type.

        The base implementation filters only on the excluded-slug list and
        title. Simba Bru's collections are coffee-only today, but filtering
        by product_type is a cheap, robust guard that keeps any
        brew-equipment or merch product (which carries a non-coffee
        product_type) out of the coffee catalogue even if one ever leaks
        into a coffee collection feed.

        Args:
            store_url: URL of the products.json endpoint

        Returns:
            List of canonical coffee product URLs
        """
        products = await self._fetch_all_shopify_products(store_url)
        found_urls = []

        for product in products:
            handle = product.get("handle")
            if not handle:
                continue

            # Skip explicitly excluded product slugs (substring match on handle)
            if any(slug in handle for slug in self.exclude_slugs):
                logger.debug(f"Skipping excluded product slug: {handle}")
                continue

            product_type = (product.get("product_type") or "").strip().lower()
            if product_type and product_type not in self.coffee_product_types:
                logger.debug(f"Skipping non-coffee product (type={product.get('product_type')!r}): {handle}")
                continue

            # Build the collection-prefixed URL then normalize to canonical form.
            base_path = store_url.replace("/products.json", "")
            url = f"{base_path}/products/{handle}"
            url = self.preprocess_product_url(url)

            # Store metadata for later enrichment and stock status
            self._shopify_product_data[url] = product

            is_available = any(v.get("available", False) for v in product.get("variants", []))
            self._shopify_stock_status[url] = is_available

            # Filter out non-coffee products using base class logic
            if self.is_coffee_product_url(url) and self.is_coffee_product_name(product.get("title", "")):
                found_urls.append(url)

        # A product may appear in multiple coffee collections; count each
        # canonical URL once. Dedup on the already-formatted canonical URLs.
        return self.deduplicate_urls(found_urls)

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Simba Bru product URLs.

        The live site canonicalizes product pages to the no-collection form
        ``/products/<handle>`` (confirmed via ``rel=canonical`` and
        ``og:url``), so strip the collection segment that the products.json
        base URL injects.
        """
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0]
            return f"{self.base_url}/products/{handle}"
        return url
