"""Chimney Fire Coffee scraper implementation with Shopify JSON extraction.

Chimney Fire Coffee is an independent coffee roastery based in the Surrey
Hills, UK, supplying ethically sourced coffee beans across the United Kingdom.
The store is Shopify-hosted and prices its products in GBP (£).
"""

import logging

from bs4 import BeautifulSoup

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)

# curl_cffi requests can be geo/market-detected to a non-home market, which
# would return the catalog priced in a converted currency instead of GBP.
# Pinning country=GB selects the roaster's home market so the returned
# products.json is always priced in the base GBP currency.
_MARKET_PARAM = "country=GB"


@register_scraper(
    name="chimney-fire",
    display_name="Chimney Fire",
    roaster_name="Chimney Fire",
    website="https://chimneyfirecoffee.com",
    description="Independent specialty coffee roastery based in the Surrey Hills, UK, "
    "supplying ethically sourced coffee beans to homes and businesses across the United Kingdom",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class ChimneyFireScraper(ShopifyJsonScraper):
    """Scraper for Chimney Fire Coffee (chimneyfirecoffee.com) using Shopify products.json.

    Only the roaster's ``/collections/coffee`` collection (the "Coffee" beans
    collection) is scraped; it contains the single origins, blends, and decaf
    beans. Subscriptions, compostable pods, and other non-bean products that
    appear in the collection are skipped via ``exclude_slugs``.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize the Chimney Fire scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Chimney Fire",
            base_url="https://chimneyfirecoffee.com",
            products_json_urls=["https://chimneyfirecoffee.com/collections/coffee/products.json"],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # The coffee collection is the curated beans collection, but it still
        # carries subscriptions, compostable pods, and gift packs. Exclude the
        # genuine equipment/services/subscription items while keeping any
        # sampler/taster/variety packs so they are flagged for review instead
        # of silently dropped (see KIT_REVIEW.md).
        self.exclude_slugs = [
            "subscription",
            "pods",
            "gift-card",
            "gift-certificate",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "apparel",
            "mug",
            "tumbler",
            "hoodie",
            "tshirt",
            "capsules",
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

    async def fetch_page(self, url: str, retries: int = 0, use_playwright: bool = False) -> BeautifulSoup | None:
        """Fetch a product page with the UK market pinned.

        The storefront may geolocate curl_cffi requests to a non-UK market,
        which would render prices in a converted currency. Pinning
        ``country=GB`` on the page URL (same param used for the products.json
        listings) keeps the rendered page in the home GBP currency so the AI
        never sees a converted amount.
        """
        separator = "&" if "?" in url else "?"
        return await super().fetch_page(
            f"{url}{separator}{_MARKET_PARAM}", retries=retries, use_playwright=use_playwright
        )

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Chimney Fire product URLs by removing the collection segment.

        The canonical product pages are ``/products/<handle>`` (no collection
        path), so strip the ``/collections/coffee`` segment built from the
        products.json URL base.
        """
        if "/collections/" in url and "/products/" in url:
            try:
                handle = url.split("/products/")[-1].split("?")[0]
                return f"{self.base_url}/products/{handle}"
            except Exception:
                return url
        return url

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Filter the product page HTML down to the product info and bean story.

        The store's product pages carry the origin/farm/variety narrative in
        ``div.Product__Info`` (title, price, description) and the
        ``div.FeatureText`` sections (e.g. "ABOUT <ORIGIN>", "Profile and
        Partnership"), which hold the bean detail that the products.json
        ``body_html`` lacks. Keeping only those gives the AI the bean
        information without page chrome. The Shopify JSON context
        (name/price/description/variants) is injected at the top of
        ``soup.body`` after this hook returns, so keeping a valid body
        preserves that data.
        """
        info = soup.select_one("div.Product__Info")
        features = soup.select("div.FeatureText")
        if info is None and not features:
            return soup

        minimal = BeautifulSoup("<html><head></head><body></body></html>", "html.parser")
        if info is not None:
            minimal.body.append(info)
        for feature in features:
            minimal.body.append(feature)
        return minimal
