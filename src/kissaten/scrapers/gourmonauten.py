"""GourmoNauten scraper implementation with AI-powered extraction (Shopify storefront).

GourmoNauten (gourmonauten.club) is a German specialty coffee roaster hosted on
Shopify. The storefront is currently password-protected (pre-launch): the whole
site redirects to ``/password`` and every storefront endpoint — including
``/products.json`` — answers HTTP 401. Because a working ``products.json`` (via
the public Storefront API) is the canonical Shopify discovery endpoint, this
scraper is written as a Shopify JSON scraper built directly on ``BaseScraper``
rather than on ``ShopifyJsonScraper``. It degrades gracefully today (no products
-> no out-of-stock updates, the base class records the failed listing fetch) and
starts returning beans the moment the store launches.

Platform notes (curl-first discovery, 2026-09):
- ``GET https://gourmonauten.club/products.json`` -> 401 (password page)
- Response body contains ``shopify.content_for_header`` / ``/cdn/shop/`` markers
  and the myshopify domain ``pvv5ic-v1.myshopify.com`` -> Shopify confirmed.
"""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="gourmonauten",
    display_name="GourmoNauten",
    roaster_name="GourmoNauten",
    website="https://gourmonauten.club",
    description="German specialty coffee roaster (Shopify storefront, currently password-protected pre-launch).",
    requires_api_key=True,
    currency="EUR",
    country="Germany",
    status="experimental",
)
class GourmonautenScraper(BaseScraper):
    """Scraper for GourmoNauten (gourmonauten.club) with AI-powered extraction."""

    # Shopify's products.json paginates at 250 products per page.
    PRODUCTS_PER_PAGE = 250
    # Safety cap so a misbehaving endpoint cannot cause an endless page loop.
    MAX_PAGES = 20

    def __init__(self, api_key: str | None = None):
        """Initialize the GourmoNauten scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="GourmoNauten",
            base_url="https://gourmonauten.club",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = None
        try:
            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
        except ValueError:
            logger.warning("Google API key not configured. AI extraction will not be available.")

    async def get_store_urls(self) -> list[str]:
        """Get the Shopify products.json catalogue URL.

        Returns:
            List containing the products.json endpoint.
        """
        return [f"https://gourmonauten.club/products.json?limit={self.PRODUCTS_PER_PAGE}"]

    async def _fetch_products_page(self, page: int) -> list[dict] | None:
        """Fetch a single products.json page.

        Args:
            page: 1-based page number.

        Returns:
            The raw product list, or None when the fetch failed (including the
            401 the password-protected pre-launch storefront returns).
        """
        url = f"https://gourmonauten.club/products.json?limit={self.PRODUCTS_PER_PAGE}&page={page}"
        try:
            response = await self.client.get(url)
        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            return None

        if response.status_code != 200:
            logger.warning(
                f"products.json returned HTTP {response.status_code} for {url} (store likely password-protected)"
            )
            return None

        try:
            payload = response.json()
        except ValueError as e:
            logger.warning(f"products.json did not return JSON for {url}: {e}")
            return None

        products = payload.get("products")
        if not isinstance(products, list):
            logger.warning(f"Unexpected products.json payload shape for {url}")
            return None
        return products

    # Sold-out detection: Shopify products.json variant availability flag.
    # A product is skipped unless at least one of its variants is available.
    # Filtering runs before is_coffee_product_url so excluded items never leak
    # past the stock check.
    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract in-stock coffee product URLs from the Shopify products.json catalogue.

        Args:
            store_url: products.json URL (used for pagination seed only).

        Returns:
            List of in-stock coffee product URLs (empty if the catalogue is unreachable).
        """
        product_urls: list[str] = []
        seen: set[str] = set()

        for page in range(1, self.MAX_PAGES + 1):
            products = await self._fetch_products_page(page)
            if products is None:
                # A failed catalogue fetch must not be mistaken for "everything
                # is sold out" — return nothing so the base class records the
                # listing failure and skips out-of-stock updates.
                return []
            if not products:
                break

            for product in products:
                handle = product.get("handle")
                if not handle:
                    continue

                variants = product.get("variants") or []
                if not any(variant.get("available") for variant in variants):
                    logger.debug(f"Skipping sold-out product: {handle}")
                    continue

                url = self.resolve_url(f"/products/{handle}")
                if not self.is_coffee_product_url(url, required_path_patterns=["/products/"]):
                    continue

                if url not in seen:
                    seen.add(url)
                    product_urls.append(url)

            logger.info(f"products.json page {page}: {len(products)} products, {len(product_urls)} coffee URLs so far")

        return product_urls

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction.

        Args:
            product_urls: List of URLs for new products.

        Returns:
            List of newly scraped CoffeeBean objects.
        """
        if not product_urls:
            return []

        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=False,
            use_optimized_mode=False,
            translate_to_english=False,
        )

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Pin the store currency (the registry lookup by display name can fall back to GBP)."""
        bean.currency = "EUR"
        return bean
