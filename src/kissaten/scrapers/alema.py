"""Alema Coffee scraper implementation with AI-powered extraction (Wix storefront).

Alema Coffee (alemacoffee.com) is a Wix storefront based in Bury St Edmunds,
Suffolk, UK. The coffee catalogue is enumerated from the ``/category/all-products``
listing, which is paginated across two pages (``?page=2``). Product detail pages
use Wix's ``/product-page/<slug>`` URL scheme. Coffee cards are
``div[data-hook="product-item-root"]`` containers carrying a
``a[href*="/product-page/"]`` link.

Whole-bean coffees are separated from equipment/merchandise at the link level by
extending the base exclusion patterns (brew bundles, keepcups, coffee scales) on
top of the default grinder/v60/filter-paper exclusions. Curated samplers/taster
packs are *not* excluded here — they are extracted and flagged
``is_tasting_kit`` / ``requires_review`` so they land in the admin review queue
instead of being silently dropped.
"""

import logging

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from . import _curl_http as httpx
from .base import BaseScraper, WebBotAuth
from .registry import register_scraper

logger = logging.getLogger(__name__)

# The whole-bean coffee catalogue lives on these two paginated listing pages.
_STORE_URLS = [
    "https://www.alemacoffee.com/category/all-products",
    "https://www.alemacoffee.com/category/all-products?page=2",
]


@register_scraper(
    name="alema",
    display_name="Alema Coffee",
    roaster_name="Alema Coffee",
    website="https://www.alemacoffee.com",
    description="Specialty coffee roaster based in Bury St Edmunds, Suffolk, United Kingdom.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class AlemaScraper(BaseScraper):
    """Scraper for Alema Coffee (alemacoffee.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize the Alema Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Alema Coffee",
            base_url="https://www.alemacoffee.com",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )
        # alemacoffee.com's edge resets the HTTP/2 stream for curl_cffi's default
        # libcurl TLS fingerprint, while the "chrome" impersonation profile
        # negotiates successfully. Rebuild the client with that profile,
        # preserving headers/auth/proxy.
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

        # The Wix storefront has no og:price:currency meta tag and no Shopify
        # currency object, so base currency detection never fires. Alema prices
        # in GBP (£); pin it and mark it as already detected so it is never
        # overwritten by a (failed) detection pass.
        self.store_currency = "GBP"
        self._currency_detected = True

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def _get_excluded_url_patterns(self) -> list[str]:
        """Extend the base exclusions with Alema's equipment/merch URL tokens."""
        base_patterns = super()._get_excluded_url_patterns()
        # Grinder, v60, filter-paper and moccamaster URLs are already covered by
        # the base patterns. These cover Alema's remaining non-coffee items.
        return [
            *base_patterns,
            "brew-bundle",  # Home Brew Bundle - Standard / Lux (brewer kits)
            "keepcup",  # Glass KeepCup (8oz) drinkware
            "scales",  # Coffee Scales
        ]

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page and narrow product detail pages to the Wix product container.

        Wix product detail pages embed all useful content inside
        ``div[data-hook="product-page"]``. Narrowing the soup to that container
        strips nav, footer, JSON blobs, and unrelated markup before the HTML is
        sent to the AI extractor, which dramatically reduces token noise.

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
            # Only narrow product detail pages, leave listing/category pages untouched
            if "/product-page/" not in (url or ""):
                return soup
            if soup is None:
                return None
            product_el = soup.select("div[data-hook='product-page']")
            if len(product_el) == 1:
                logger.debug(f"Narrowed soup to div[data-hook='product-page'] for {url}")
                return product_el[0]
            logger.warning(f"Expected 1 div[data-hook='product-page'] for {url}, found {len(product_el)}")
            return soup
        except Exception as e:
            logger.error(f"Error fetching page {url if 'url' in dir() else '?'}: {e}")
            return None

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape (the paginated all-products listing pages).

        Returns:
            List of category listing URLs to crawl for product URLs.
        """
        return list(_STORE_URLS)

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
        # Final currency guard: force GBP so the AI extractor never reports a
        # non-GBP currency for this UK roaster.
        bean.currency = "GBP"
        return bean

    # Sold-out handling: the Wix product-item-root card shows "Out of Stock" /
    # "Sold out" / "Unavailable" in the button area when a product is sold out.
    # Whole-bean coffees that are temporarily out of stock are still discovered
    # and returned here — AI extraction reads the product detail page and sets
    # ``in_stock=False`` from it, so a temporarily-sold-out coffee is never
    # dropped from the catalogue. Only genuine non-coffee items (equipment /
    # merch) are excluded, via the URL-pattern filtering below.
    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract whole-bean product URLs from the Wix store listing.

        Args:
            store_url: URL of the store/category page

        Returns:
            List of whole-bean product URLs (including temporarily sold-out coffees)
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        product_urls: list[str] = []
        seen: set[str] = set()

        for item in soup.select('[data-hook="product-item-root"]'):
            link = item.select_one('a[href*="/product-page/"]')
            if not link:
                continue
            href = link.get("href")
            if not href or not isinstance(href, str):
                continue

            # Strip query string and fragment; resolve to canonical absolute URL
            full_url = self.resolve_url(href.split("?")[0].split("#")[0])

            # Apply standard coffee-product URL filtering (uses /product-page/ path pattern)
            if not self.is_coffee_product_url(full_url, required_path_patterns=["/product-page/"]):
                continue

            if full_url not in seen:
                seen.add(full_url)
                product_urls.append(full_url)

        logger.info(f"Found {len(product_urls)} whole-bean product URLs from {store_url}")
        return product_urls
