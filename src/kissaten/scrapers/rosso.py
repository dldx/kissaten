"""Rosso Coffee Roasters scraper implementation with Shopify JSON extraction.

Rosso Coffee Roasters is a specialty coffee roaster based in Calgary, Canada.
The store is Shopify-hosted and prices its products in Canadian dollars (CAD).
"""

import logging

from bs4 import BeautifulSoup

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)

# curl_cffi requests are geo/market-detected as the USD /en-us market by
# rossocoffeeroasters.com, which serves converted prices and marks
# Shopify.currency as USD. Pinning country=CA selects the roaster's home
# market so the returned catalog is priced in the base CAD currency.
_MARKET_PARAM = "country=CA"


@register_scraper(
    name="rosso",
    display_name="Rosso",
    roaster_name="Rosso",
    website="https://www.rossocoffeeroasters.com",
    description="Calgary-based specialty coffee roaster sourcing exceptional single "
    "origins, seasonal blends, and rare geisha micro-lots in Canadian dollars",
    requires_api_key=True,
    currency="CAD",
    country="Canada",
    status="available",
)
class RossoCoffeeScraper(ShopifyJsonScraper):
    """Scraper for Rosso Coffee Roasters (rossocoffeeroasters.com) using Shopify products.json.

    Only the roaster's ``/collections/coffee`` collection (the "Coffee" nav
    collection) is scraped; it contains the beans, seasonal blends, and instant
    coffees and deliberately omits equipment/tea/gift-card products that live
    in ``collections/all``.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize the Rosso scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Rosso",
            base_url="https://www.rossocoffeeroasters.com",
            products_json_urls=["https://www.rossocoffeeroasters.com/collections/coffee/products.json"],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # The coffee collection is already clean of equipment/tea/merch, but keep
        # a small guard list so any non-bean product that sneaks into the
        # collection is still skipped.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "tea",
            "chai",
            "yerba-mate",
        ]

        # The storefront geolocates curl_cffi requests to the USD /en-us market
        # (see _fetch_all_shopify_products). Force the roaster's base CAD
        # currency and mark it as detected so the collection-page detection
        # path in _scrape_new_products (which would see the USD market) is
        # skipped.
        self.store_currency = "CAD"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def _fetch_all_shopify_products(self, products_json_url: str) -> list[dict]:
        """Fetch all products from the products.json endpoint with the Canadian market pinned.

        Mirrors ``ShopifyJsonScraper._fetch_all_shopify_products`` but appends
        ``country=CA`` to each paginated request. Without it, curl_cffi requests
        are geo/market-detected as the USD /en-us market and the returned catalog
        is priced in converted USD amounts instead of the home CAD currency.
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
        """Fetch a product page with the Canadian market pinned.

        The storefront geolocates curl_cffi requests to the USD /en-us market,
        which renders prices in converted USD amounts. Pinning ``country=CA`` on
        the page URL (same param used for the products.json listings) keeps the
        rendered page in the home CAD currency so the AI never sees a USD amount.
        """
        separator = "&" if "?" in url else "?"
        return await super().fetch_page(
            f"{url}{separator}{_MARKET_PARAM}", retries=retries, use_playwright=use_playwright
        )

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Rosso product URLs by removing the collection segment.

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
        """Filter the product page HTML down to the bean detail accordions.

        Rosso hides origin/process/variety/geography and the farm story behind
        collapsible ``div.product-block-collapsible-tab`` sections, so we keep
        only those to give the AI the bean information without page chrome.
        The Shopify JSON context (name/price/description/variants) is injected
        at the top of ``soup.body`` after this hook returns, so keeping a valid
        body preserves that data.
        """
        accordions = soup.select("div.product-block-collapsible-tab")
        if not accordions:
            return soup

        minimal = BeautifulSoup("<html><head></head><body></body></html>", "html.parser")
        for accordion in accordions:
            minimal.body.append(accordion)
        return minimal
