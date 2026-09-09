"""Pilot Coffee Roasters scraper implementation with Shopify JSON extraction."""

import logging

from bs4 import BeautifulSoup

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)

# Pin the Shopify Markets country so paginated products.json fetches always
# return the home-market catalog priced in CAD, regardless of the caller's
# geolocated IP (Pilot serves Canada/US markets with currency conversion).
_MARKET_PARAM = "country=CA"

# ShopifyJsonScraper builds product URLs from the products.json base, which
# yields "/collections/coffee/products/<handle>". Pilot's canonical product
# pages are served at "/products/<handle>" (no collection segment).
_COLLECTION_SEGMENT = "/collections/coffee"


@register_scraper(
    name="pilot-coffee-roasters",
    display_name="Pilot Coffee Roasters",
    roaster_name="Pilot Coffee Roasters",
    website="https://pilotcoffeeroasters.com",
    description="Toronto-based specialty coffee roaster (founded 2009 as Te Aro Roasted) known for "
    "direct-trade single origins and blends served across its Toronto cafe network",
    requires_api_key=True,
    currency="CAD",
    country="Canada",
    status="available",
)
class PilotCoffeeRoastersScraper(ShopifyJsonScraper):
    """Scraper for Pilot Coffee Roasters (pilotcoffeeroasters.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Pilot Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Pilot Coffee Roasters",
            base_url="https://pilotcoffeeroasters.com",
            products_json_urls=["https://pilotcoffeeroasters.com/collections/coffee/products.json"],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # The storefront serves the Canadian market by default (Shopify.currency
        # "CAD" rate 1.0). Pin CAD so a geo-localized storefront (which Shopify
        # can serve to non-local clients) can't convert prices.
        self.store_currency = "CAD"
        self._currency_detected = True

        # The /collections/coffee collection is a curated bean list, but it also
        # carries instant coffee and ready-to-drink nitro cold brew. Keep a small
        # exclude list as a safety net against those plus any future
        # subscription/merch products. Tasting kits / samplers are NOT excluded —
        # they flow through with is_tasting_kit / requires_review flags.
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "instant",  # soluble coffee, not whole bean
            "nitro",  # ready-to-drink cold brew, not beans
            "tea",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def _fetch_all_shopify_products(self, products_json_url: str) -> list[dict]:
        """Fetch all products from the products.json endpoint with the CA market pinned.

        Mirrors ``ShopifyJsonScraper._fetch_all_shopify_products`` but appends
        ``country=CA`` to each paginated request so a geo-detecting storefront
        can't return a US-converted catalog/pricing.
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
        """Strip the collection segment to match Pilot's canonical product URLs.

        ShopifyJsonScraper builds product URLs as
        ``<products.json base>/products/<handle>``, which yields a
        ``/collections/coffee/products/<handle>`` form. Pilot's real product
        pages are served at ``/products/<handle>`` (querying the ``/products/``
        form directly returns 200), so normalize the URL to that form.
        """
        return url.replace(_COLLECTION_SEGMENT, "", 1)

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Prune the product page HTML down to the bean detail elements.

        Pilot renders bean specifics as:

        * tasting notes in ``span.metafield-multi_line_text_field`` elements
          (e.g. "Strawberry • Yuzu • Juicy") inside the product-info column;
        * a ``div.text-with-icons`` band with Varietal / Process / Altitude /
          Origin entries (single origins only — blends omit it).

        Everything else (carousels, reviews, related products, brew-guide
        sections) is page chrome the Shopify JSON context doesn't need. We
        build a new minimal soup WITH a body: ShopifyJsonScraper injects the
        Shopify product JSON at the top of ``soup.body`` AFTER this hook
        returns, so keeping a valid body preserves name/price/variants.
        """
        kept: list = []
        seen_ids: set[int] = set()

        for span in soup.select("span.metafield-multi_line_text_field"):
            block = span.find_parent("div", class_="product-info__block-item") or span
            if id(block) not in seen_ids:
                seen_ids.add(id(block))
                kept.append(block)

        spec_band = soup.select_one("div.text-with-icons")
        if spec_band is not None and id(spec_band) not in seen_ids:
            kept.append(spec_band)

        if not kept:
            return soup

        minimal = BeautifulSoup("<html><head></head><body></body></html>", "html.parser")
        for element in kept:
            minimal.body.append(element)
        return minimal
