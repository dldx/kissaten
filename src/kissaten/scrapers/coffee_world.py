"""Coffee World scraper implementation with Shopify JSON extraction.

Coffee World (coffeeworld.co.uk) is a UK coffee retailer based in
Wolverhampton, supplying single origin coffees, blends, decaf and curated
multi-bag coffee bundles. The store is Shopify-hosted and prices its
products in GBP (£).
"""

import logging
import re

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)

# curl_cffi requests can be geo/market-detected to a non-home market, which
# would return the catalog priced in a converted currency instead of GBP.
# Pinning country=GB selects the roaster's home market so the returned
# products.json is always priced in the base GBP currency.
_MARKET_PARAM = "country=GB"

# Fixed multi-bag coffee bundles (e.g. "sweet-like-chocolate-3-x-250g-bundle")
# are curated sampler-style variety packs of several different coffees. Their
# handles carry a "<n>-x-<weight>g" token that no single-origin bean handle
# uses, which lets us flag exactly those products as tasting kits.
_MULTI_BAG_BUNDLE_RE = re.compile(r"\d-x-\d")


@register_scraper(
    name="coffee-world",
    display_name="Coffee World",
    roaster_name="Coffee World",
    website="https://coffeeworld.co.uk",
    description="UK coffee retailer based in Wolverhampton supplying single "
    "origin coffees, blends, decaf and curated multi-bag coffee bundles",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class CoffeeWorldScraper(ShopifyJsonScraper):
    """Scraper for Coffee World (coffeeworld.co.uk) using Shopify products.json.

    Two curated collections are scraped:

    * ``/collections/coffee`` — the roasted-coffee collection (single
      origins, blends, decaf). Subscriptions (the "Selection" products, the
      "Roasters Choice" subscription), green (unroasted) coffee, and the
      subscription bundle-builder page are excluded.
    * ``/collections/coffee-bundles`` — fixed multi-bag coffee bundles are
      genuine sampler-style variety packs and are kept (flagged as tasting
      kits for admin review); equipment gift boxes (V60 / Aeropress / moka
      pot / cafetiere gift sets), home espresso machine packages, and the
      subscription bundle-builder are excluded.

    The ``body_html`` of the products.json carries structured
    ``Taste Notes:`` / ``Origin:`` / ``Process:`` / ``Roast:`` / ``Best For:``
    labels plus descriptive prose, and the variants carry the weight/price
    options, so pure JSON-only extraction (``scrape_product_pages=False``)
    is sufficient — the 1.3 MB product pages add nothing the JSON lacks.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize the Coffee World scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Coffee World",
            base_url="https://coffeeworld.co.uk",
            products_json_urls=[
                "https://coffeeworld.co.uk/collections/coffee/products.json",
                "https://coffeeworld.co.uk/collections/coffee-bundles/products.json",
            ],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The collections are curated to coffee but still carry subscriptions,
        # green (unroasted) coffee, and equipment bundles. Exclude the genuine
        # equipment/services while keeping the multi-bag coffee bundles so they
        # are flagged for review instead of silently dropped (see KIT_REVIEW.md).
        self.exclude_slugs = [
            # Green (unroasted) coffee is not a roasted bean.
            "green-coffee",
            # Subscriptions & the subscription bundle-builder page.
            "roasters-choice",  # "Roasters Choice Subscription"
            "selection",  # "Espresso Selection", "Filter Selection", ...
            "subscription",  # "Office Coffee Subscription"
            "subscribe",  # "Create your coffee bundles & save when you subscribe."
            # Equipment bundles & gift boxes in the coffee-bundles collection.
            "gift-box",
            "home-espresso-package",
        ]

        # The storefront may geolocate curl_cffi requests to a non-UK market
        # (see _fetch_all_shopify_products). Force the roaster's home GBP
        # currency and mark it as detected so the collection-page detection
        # path in _scrape_new_products (which could see a converted market) is
        # skipped.
        self.store_currency = "GBP"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def _fetch_all_shopify_products(self, products_json_url: str) -> list[dict]:
        """Fetch all products from the products.json endpoint with the UK market pinned.

        Mirrors ``ShopifyJsonScraper._fetch_all_shopify_products`` but appends
        ``country=GB`` to each paginated request. Without it, curl_cffi requests
        can be geo/market-detected to a converted-currency market instead of the
        home GBP currency.
        """
        all_products = []
        page = 1
        limit = 250

        while True:
            url = f"{products_json_url}?{_MARKET_PARAM}&limit={limit}&page={page}"
            logger.info(f"Fetching Shopify products: {url}")

            data, use_playwright = await self._fetch_page_with_escalation(url)
            if data is None:
                if products_json_url not in self._failed_listing_urls:
                    self._failed_listing_urls.append(products_json_url)
                break

            products = data.get("products", [])
            if not products:
                break

            all_products.extend(products)
            logger.debug(f"Fetched {len(products)} products from page {page}")

            if len(products) < limit:
                break

            page += 1
            if use_playwright:
                logger.debug(f"Page {page - 1} escalated to Playwright; re-attempting httpx on page {page}.")

        return all_products

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Coffee World product URLs by removing the collection segment.

        The canonical product pages are ``/products/<handle>`` (no collection
        path), so strip the ``/collections/coffee`` / ``/collections/coffee-bundles``
        segment built from the products.json URL base.
        """
        if "/collections/" in url and "/products/" in url:
            try:
                handle = url.split("/products/")[-1].split("?")[0]
                return f"{self.base_url}/products/{handle}"
            except Exception:
                return url
        return url

    def postprocess_review_flags(self, bean, url: str):
        """Flag fixed multi-bag coffee bundles as tasting kits for review.

        The multi-bag bundles (e.g. "Riding the Wave - 3 x 200g Bundle") are
        curated variety packs of several different coffees, so they are
        treated like sampler kits: kept in the catalogue but routed to the
        admin review queue (``requires_review``) instead of public search.
        """
        if bean is not None and _MULTI_BAG_BUNDLE_RE.search(str(url)):
            bean.is_tasting_kit = True
        return bean
