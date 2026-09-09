"""The Angry Roaster scraper implementation with Shopify JSON extraction."""

import logging

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)

_COLLECTION_SEGMENT = "/collections/coffee"
# curl_cffi requests are geo/market-detected by Shopify Markets: with a
# datacenter IP the store serves US-converted prices (e.g. 16.28 instead of
# 22.00 CAD). Passing country=CA pins the Canadian market so products.json
# returns the home-market CAD prices.
_MARKET_PARAM = "country=CA"


@register_scraper(
    name="the-angry-roaster",
    display_name="The Angry Roaster",
    roaster_name="The Angry Roaster",
    website="https://theangryroaster.com",
    description="Canadian specialty coffee roaster based in Burlington, Ontario, "
    "with a loud, anti-establishment brand and a small rotating menu of "
    "single-origin coffees plus decaf and instant options.",
    requires_api_key=True,
    currency="CAD",
    country="Canada",
    status="available",
)
class TheAngryRoasterScraper(ShopifyJsonScraper):
    """Scraper for The Angry Roaster (theangryroaster.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize The Angry Roaster scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="The Angry Roaster",
            base_url="https://theangryroaster.com",
            products_json_urls=["https://theangryroaster.com/collections/coffee/products.json"],
            scrape_product_pages=False,
            cache_product_pages=False,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # The storefront serves the Canadian market by default (Shopify country
        # "Canada", currencyCode "CAD" per the privacy policy; the site shows
        # $ CAD prices). Pin CAD so a geo-localized storefront (which Shopify
        # Markets serves to datacenter IPs) can't stamp converted prices with
        # the wrong currency; the CA market param below does the same for the
        # underlying prices themselves.
        self.store_currency = "CAD"
        self._currency_detected = True

        # The /collections/coffee collection is a curated bean list, so only a
        # small exclude list is needed as a safety net. Tasting kits / samplers
        # are intentionally NOT excluded — they flow through with
        # is_tasting_kit / requires_review flags for admin review.
        self.exclude_slugs = [
            "gift-card",
            "subscription",
            "wholesale",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def _fetch_all_shopify_products(self, products_json_url: str) -> list[dict]:
        """Fetch all products from the products.json endpoint with the CA market pinned.

        Mirrors ``ShopifyJsonScraper._fetch_all_shopify_products`` but appends
        ``country=CA`` to each paginated request. Without it, curl_cffi requests
        are geo/market-detected and the store serves US-converted prices
        (verified: country=US returns e.g. 16.28 instead of 22.00 CAD for The
        Mad House Roast).
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
        """Strip the collection segment to match The Angry Roaster's canonical product URLs.

        ShopifyJsonScraper builds product URLs as
        ``<products.json base>/products/<handle>``, which yields a
        ``/collections/coffee/products/<handle>`` form. The site's real product
        pages are served at ``/products/<handle>`` (that form is what the
        collection page links to and it returns 200 directly), so normalize
        the URL to that form.
        """
        return url.replace(_COLLECTION_SEGMENT, "")
