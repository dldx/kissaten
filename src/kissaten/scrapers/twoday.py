"""TwoDay Coffee Roasters scraper implementation with AI-powered extraction.

TwoDay Coffee Roasters (twodaycoffee.co.uk) is a Bristol, UK roaster running a
custom e-commerce platform (no Shopify products.json, no WordPress/WooCommerce
REST API, no sitemap.xml). The coffee catalogue lives on the single ``/shop/``
listing page. Coffee cards are ``div[data-mh="product-details"]`` containers
whose ``.product__title a`` links to ``/shop/products/<slug>/`` (priced "£X per
100g"), while accessory cards (``div[data-mh="accessory-details"]``) expose no
product link, so the coffee set is cleanly separated at the link level. Product
detail pages use the ``main`` container.
"""

import logging

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from . import _curl_http as httpx
from .base import BaseScraper, WebBotAuth
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="twoday",
    display_name="TwoDay Coffee Roasters",
    roaster_name="TwoDay Coffee Roasters",
    website="https://twodaycoffee.co.uk",
    description="Bristol, UK specialty coffee roaster (custom e-commerce).",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class TwoDayScraper(BaseScraper):
    """Scraper for TwoDay Coffee Roasters (twodaycoffee.co.uk)."""

    def __init__(self, api_key: str | None = None):
        """Initialize the TwoDay scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="TwoDay Coffee Roasters",
            base_url="https://twodaycoffee.co.uk",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )
        # twodaycoffee.co.uk's edge rejects curl_cffi's default libcurl TLS
        # fingerprint (curl: (35) BAD_DECRYPT on every attempt), while the
        # "chrome" impersonation profile negotiates successfully. Rebuild the
        # client with that profile, preserving headers/auth/proxy.
        proxy_url = self.https_proxy or self.http_proxy
        client_kwargs: dict = {
            "headers": self.headers,
            "timeout": self.timeout,
            "auth": WebBotAuth(self),
            "impersonate": "chrome",
        }
        if proxy_url:
            client_kwargs["proxy"] = proxy_url
        self.client = httpx.AsyncClient(**client_kwargs)
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page and narrow product detail pages to the ``main`` container.

        TwoDay product detail pages embed all useful content (name, price,
        origin, roast, description) inside the ``main`` container. Narrowing the
        soup to that container strips nav, footer, JS blobs, and unrelated
        markup before the HTML reaches the AI extractor, keeping token usage
        low. Listing pages (``/shop/``) are left untouched.

        Args:
            *args: Positional arguments forwarded to the base fetch_page.
            **kwargs: Keyword arguments forwarded to the base fetch_page.

        Returns:
            BeautifulSoup object (narrowed for product pages) or None if fetch failed.
        """
        try:
            soup = await super().fetch_page(*args, **kwargs)
            url = kwargs.get("url")
            if not url and len(args) > 0:
                url = args[0]
            # Only narrow product detail pages ("/shop/products/..."), leave the
            # listing page ("/shop/") untouched.
            if "/shop/products/" not in (url or ""):
                return soup
            if soup is None:
                return None
            main_el = soup.select("main")
            if len(main_el) == 1:
                logger.debug(f"Narrowed soup to main for {url}")
                return main_el[0]
            logger.warning(f"Expected 1 main for {url}, found {len(main_el)}")
            return soup
        except Exception as e:
            logger.error(f"Error fetching page {url if 'url' in dir() else '?'}: {e}")
            return None

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape (the single /shop/ listing page)."""
        return ["https://twodaycoffee.co.uk/shop/"]

    async def _scrape_new_products(
        self, product_urls: list[str], use_optimized_mode: bool = False
    ) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction.

        Args:
            product_urls: List of URLs for new products
            use_optimized_mode: Whether to use optimized (visual) extraction mode

        Returns:
            List of newly scraped CoffeeBean objects
        """
        if not product_urls:
            return []

        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=False,
            use_optimized_mode=use_optimized_mode,
        )

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        # The custom platform has no og:price:currency meta tag, so the base
        # class currency detection never fires and default_currency falls back
        # to the registry default. TwoDay prices in GBP (£); force it.
        bean.currency = "GBP"
        return bean

    # Sold-out detection: no explicit sold-out marker exists on this custom
    # listing (the only "oos" on the page is "gooseberry" in a tasting note).
    # Coffee and accessory cards are separated structurally: coffee cards are
    # div[data-mh="product-details"] containers carrying a
    # ".product__title a[href*='/shop/products/']" link, while accessory cards
    # (div[data-mh="accessory-details"]) expose no product link. We extract only
    # coffee-card product links (defensively skipping a card if it textually
    # reads as sold out) and run is_coffee_product_url before adding, so any
    # stray non-coffee link is filtered before it leaks past.
    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract coffee product URLs from the /shop/ listing page.

        Args:
            store_url: URL of the store/listing page

        Returns:
            List of coffee product URLs
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        product_urls: list[str] = []
        seen: set[str] = set()

        # Coffee cards are div[data-mh="product-details"]; accessory cards are
        # div[data-mh="accessory-details"] and contain no product links.
        for card in soup.select('div[data-mh="product-details"]'):
            # Defensive sold-out check on the specific card (no marker observed).
            card_text = card.get_text(" ", strip=True).lower()
            if any(token in card_text for token in ("sold out", "out of stock", "unavailable")):
                continue
            link = card.select_one('a[href*="/shop/products/"]')
            if not link:
                continue
            href = link.get("href")
            if not href or not isinstance(href, str):
                continue
            full_url = self.resolve_url(href)
            if self.is_coffee_product_url(full_url, required_path_patterns=["/shop/products/"]):
                if full_url not in seen:
                    seen.add(full_url)
                    product_urls.append(full_url)

        logger.info(f"Found {len(product_urls)} coffee product URLs from {store_url}")
        return product_urls
