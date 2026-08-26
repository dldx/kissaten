"""White Star Coffee scraper implementation with AI-powered extraction.

White Star Coffee is a Belfast-based specialty coffee roaster. The site is
Shopify-hosted (product imagery is served from cdn.shopify.com) but uses a
customers: ``/products.json`` and ``/collections.json`` both return
404, and the server-rendered storefront only resolves on the canonical host
``whitestar.coffee`` (the ``whitestarcoffee.co.uk`` alias serves the homepage
but 404s every ``/shop/*`` route). Product URLs follow the pattern
``/shop/coffee/<handle>`` with a required ``?id=<variant_id>`` query param:
the storefront 404s the no-query form, so we keep the full query-carrying
URL (the site's own ``<link rel="canonical">`` strips the param, but the
stripped URL does not render).
"""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="white-star",
    display_name="White Star Coffee",
    roaster_name="White Star Coffee",
    website="https://whitestar.coffee",
    description="Belfast-based specialty coffee roaster known for small-lot, "
    "high-scoring single origins from Costa Rica, Colombia and beyond",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class WhiteStarScraper(BaseScraper):
    """Scraper for White Star Coffee (whitestar.coffee) using AI extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize White Star scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="White Star Coffee",
            base_url="https://whitestar.coffee",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Pin the store currency (GBP) so the geo-detected value can't override.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the coffee collection URL
        """
        return ["https://whitestar.coffee/shop/coffee"]

    def _is_sold_out(self, link) -> bool:
        """Return True if the product card behind a listing link is sold out.

        # Sold-out detection: text detection on the product card ancestor.
        Walks a few ancestors up from the ``<a>`` and looks for a stock marker
        in the card container text. Runs before the coffee-URL filter so
        sold-out products never leak past the stock check.
        """
        node = link
        for _ in range(4):
            node = node.parent
            if node is None:
                return False
            text = node.get_text(" ", strip=True).lower()
            if any(marker in text for marker in ("sold out", "out of stock", "unavailable")):
                return True
        return False

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract canonical product URLs from the coffee listing page.

        Args:
            store_url: URL of the store page

        Returns:
            List of product URLs (each carrying its required ``?id=`` variant param)
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        product_urls = []
        for link in soup.select('a[href*="/shop/coffee/"]'):
            href = link.get("href")
            if not isinstance(href, str) or not href:
                continue

            # Skip sold-out products first (see _is_sold_out).
            if self._is_sold_out(link):
                logger.debug(f"Skipping sold-out product card: {href}")
                continue

            # Keep the ?id=<variant_id> query param. The storefront 404s the
            # no-query canonical form, so the variant id is required for the
            # product page to render.
            full_url = self.resolve_url(href)

            if not self.is_coffee_product_url(full_url, required_path_patterns=["/shop/coffee/"]):
                continue

            if full_url not in product_urls:
                product_urls.append(full_url)

        return self.deduplicate_urls(product_urls)

    async def _scrape_new_products(
        self, product_urls: list[str], use_optimized_mode: bool = False
    ) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction.

        Args:
            product_urls: List of URLs for new products
            use_optimized_mode: Unused; provided to match the base signature.

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
            use_optimized_mode=False,
        )

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Pin the store currency on extracted beans.

        Args:
            bean: Extracted CoffeeBean object

        Returns:
            Postprocessed CoffeeBean object
        """
        bean.currency = self.store_currency
        return super().postprocess_extracted_bean(bean)
