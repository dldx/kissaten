"""Café Pista scraper implementation with Shopify JSON extraction.

Café Pista (cafepista.com) is a Montréal, Québec specialty roaster. The
storefront is French-first bilingual (French default, /en/ available); the
Shopify catalog data (`titles`, `body_html`, `product_type`) is in French, so
extraction forces ``translate_to_english=True``.

The catalog mixes three price channels for the same coffees:

* retail products (``Sac de café`` product type, handles like ``bookkisa``);
* wholesale / private-label channel duplicates tagged ``wholesale-only``
  (handles like ``saison_ws``, ``la-linda-ws``, whitelabel partner bags) at
  lower bulk prices;
* subscription products tagged ``subscription`` / ``office_subscription``.

We scrape ``collections/all/products.json`` filtered to ``product_type ==
"Sac de café"`` with ``wholesale-only`` and ``subscription`` tags removed, so
the retail catalog (including sold-out items, which curated collections drop)
is covered while wholesale/subscription duplicates never reach the pipeline.
"""

import logging

from bs4 import BeautifulSoup

from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)

# curl_cffi requests are geo/market-detected as the UK (GBP) market by Shopify
# Markets, which converts every price (e.g. Bookkisa 28.00 CAD -> 16.00 GBP).
# Pinning country=CA selects the roaster's home market so products.json, the
# rendered product pages, and the currency detection all stay in CAD.
_MARKET_PARAM = "country=CA"


@register_scraper(
    name="cafe-pista",
    display_name="Café Pista",
    roaster_name="Café Pista",
    website="https://cafepista.com",
    description="Montréal specialty coffee roaster founded in 2014 as a human-powered "
    "bike café, roasting on a low-emission Loring machine with published price "
    "transparency (price paid per pound vs C-market) on single-origin coffees",
    requires_api_key=True,
    currency="CAD",
    country="Canada",
    status="available",
)
class CafePistaScraper(ShopifyJsonScraper):
    """Scraper for Café Pista (cafepista.com) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Café Pista scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Café Pista",
            base_url="https://cafepista.com",
            products_json_urls=["https://cafepista.com/collections/all/products.json"],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Shopify Markets geolocates curl_cffi requests to the UK (GBP). Force
        # the home currency to CAD and mark it as detected so the collection-page
        # detection path in _scrape_new_products (which would see the GBP market)
        # is skipped and postprocess_extracted_bean stamps CAD on every bean.
        self.store_currency = "CAD"
        self._currency_detected = True

        # Retail-only products are selected via product_type/tag filters in
        # _extract_product_urls_from_store; this list is a belt-and-braces
        # guard for the stock-update path.
        self.exclude_slugs = [
            "abonnement",  # subscriptions (Abonnement Bureau / Mensuel / prépayés)
            "gift-card",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def _fetch_all_shopify_products(self, products_json_url: str) -> list[dict]:
        """Fetch all products from products.json with the Canadian market pinned.

        Mirrors ``ShopifyJsonScraper._fetch_all_shopify_products`` but appends
        ``country=CA`` to each paginated request. Without it, Shopify Markets
        geo-converts the catalog to GBP for datacenter IPs.
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

        The storefront renders geo-converted GBP prices for datacenter IPs;
        appending ``country=CA`` (same param as the products.json listings)
        keeps the rendered page in the home CAD currency so the AI never sees
        a converted amount.
        """
        separator = "&" if "?" in url else "?"
        return await super().fetch_page(
            f"{url}{separator}{_MARKET_PARAM}", retries=retries, use_playwright=use_playwright
        )

    def preprocess_product_url(self, url: str) -> str:
        """Standardize Café Pista product URLs by removing the collection segment.

        The site's own product links are ``/products/<handle>`` (no collection
        path), so strip the ``/collections/all`` segment built from the
        products.json URL base.
        """
        if "/collections/" in url and "/products/" in url:
            try:
                handle = url.split("/products/")[-1].split("?")[0]
                return f"{self.base_url}/products/{handle}"
            except Exception:
                return url
        return url

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract retail coffee-bag product URLs from products.json.

        The default base-class filters can't separate Café Pista's price
        channels, so filter explicitly on the French Shopify product type
        ``Sac de café`` and drop the ``wholesale-only`` (wholesale +
        private-label partner bags) and ``subscription`` tagged duplicates.
        Curated samplers/trios (Trio de cafés, Ensemble dégustation) are kept —
        they flow through flagged ``is_tasting_kit``/``requires_review``.
        """
        products = await self._fetch_all_shopify_products(store_url)
        found_urls = []

        for product in products:
            handle = product.get("handle")
            if not handle:
                continue

            # Only accept products Shopify classifies as coffee bags.
            if product.get("product_type", "") != "Sac de café":
                logger.debug(f"Skipping non-coffee product type: {handle} ({product.get('product_type')})")
                continue

            # Skip wholesale/private-label and subscription channel duplicates.
            tags = product.get("tags", []) or []
            if "wholesale-only" in tags or "subscription" in tags or "office_subscription" in tags:
                logger.debug(f"Skipping wholesale/subscription tagged product: {handle}")
                continue

            # Skip explicitly excluded product slugs (substring match on handle).
            if any(slug in handle for slug in self.exclude_slugs):
                logger.debug(f"Skipping excluded product slug: {handle}")
                continue

            # Build product URL using the base of the products.json URL.
            base_path = store_url.replace("/products.json", "")
            url = f"{base_path}/products/{handle}"

            # Preprocess the URL (strip the collection segment).
            url = self.preprocess_product_url(url)

            # Store metadata for later enrichment and stock status.
            self._shopify_product_data[url] = product

            # A product is in stock if any of its variants are available.
            is_available = any(v.get("available", False) for v in product.get("variants", []))
            self._shopify_stock_status[url] = is_available

            # Filter out non-coffee products using base class logic.
            if self.is_coffee_product_url(url) and self.is_coffee_product_name(product.get("title", "")):
                found_urls.append(url)

        # Dedup on the canonical/formatted URLs (post-preprocess) so products
        # appearing multiple times are counted once.
        return self.deduplicate_urls(found_urls)

    def _get_tasting_kit_url_patterns(self) -> list[str]:
        """Add French sampler/trio URL patterns to the base kit patterns.

        Café Pista sells curated boxes ("Trio de cafés", "Ensemble dégustation",
        "Boîte d'échantillons") whose handles carry French tokens the base
        patterns miss. They must be flagged ``is_tasting_kit``/``requires_review``
        for the admin review queue, not silently scraped as single coffees.
        """
        return super()._get_tasting_kit_url_patterns() + [
            "trio-de-cafes",
            "trio-lots",
            "degustation",
            "dechantillons",
            "echantillon",
            "coffret",
        ]

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Filter the product page HTML down to the product information section.

        Café Pista's theme (Shopify Horizon) puts the title, the origin detail
        block (Région / Variété / Altitude / Producteur), the tasting-note
        description, and the Transparence / Torréfaction / Livraison accordions
        inside ``div.product-information``. The Transparence accordion carries
        price-transparency data (price paid per lb vs C-market, importer
        partnership, lot size/quality) that the products.json ``body_html``
        lacks. Everything else (nav, banners, recommendations, reviews, footer)
        is page chrome the AI doesn't need.

        The Shopify JSON context (name/price/variants) is injected at the top
        of ``soup.body`` after this hook returns, so keeping a valid body
        preserves that data.
        """
        info = soup.find("div", class_="product-information")
        if not info:
            return soup

        minimal = BeautifulSoup("<html><head></head><body></body></html>", "html.parser")
        minimal.body.append(info)
        return minimal

    async def _extract_bean_with_ai(
        self,
        ai_extractor,
        soup: BeautifulSoup,
        product_url: str,
        use_optimized_mode: bool = False,
        translate_to_english: bool = False,
    ) -> object | None:
        """Extract bean with AI, always translating French content to English."""
        return await super()._extract_bean_with_ai(
            ai_extractor=ai_extractor,
            soup=soup,
            product_url=product_url,
            use_optimized_mode=use_optimized_mode,
            translate_to_english=True,
        )
