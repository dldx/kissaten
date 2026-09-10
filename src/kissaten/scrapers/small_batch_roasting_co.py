"""Small Batch Roasting Co. scraper implementation with AI-powered extraction (WooCommerce).

Small Batch Roasting Co. is a specialty coffee roaster based in Melbourne, Australia.
The storefront runs on WordPress/WooCommerce with product permalinks of the form
`/shop/<product-category>/<product-slug>/`. Prices are in AUD.

Note on naming: This is the Melbourne (AU) roaster ("Small Batch Roasting Co.",
folder data/roasters/small_batch), distinct from "Small Batch Coffee Roasters"
in Brighton & Hove (UK, folder data/roasters/small_batch_coffee_roasters).
"""

import logging
import re

from bs4 import Tag

from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="small-batch-roasting-co",
    display_name="Small Batch Roasting Co.",
    roaster_name="Small Batch",
    website="https://www.smallbatch.com.au",
    description="Melbourne-based specialty coffee roaster (WooCommerce), known for espresso and "
    "filter single-origin coffees.",
    requires_api_key=True,
    currency="AUD",
    country="Australia",
    status="available",
)
class SmallBatchRoastingCoScraper(BaseScraper):
    """Scraper for Small Batch Roasting Co. (smallbatch.com.au) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Small Batch Roasting Co. scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Small Batch",
            base_url="https://www.smallbatch.com.au",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )
        self.store_currency = "AUD"
        self._currency_detected = True

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
        else:
            try:
                from ..ai import CoffeeDataExtractor

                self.ai_extractor = CoffeeDataExtractor()
            except Exception:
                self.ai_extractor = None

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape (coffee product categories)."""
        return [
            "https://www.smallbatch.com.au/product-category/espresso/",
            "https://www.smallbatch.com.au/product-category/filter/",
            "https://www.smallbatch.com.au/product-category/bundles/",
        ]

    async def _scrape_new_products(self, product_urls: list[str], use_optimized_mode: bool = False) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction."""
        if not product_urls:
            return []

        if not hasattr(self, "ai_extractor") or self.ai_extractor is None:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor()

        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=False,
            use_optimized_mode=use_optimized_mode,
        )

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        bean.currency = "AUD"
        return bean

    def _get_tasting_kit_url_patterns(self) -> list[str]:
        return super()._get_tasting_kit_url_patterns() + ["bundle", "4_bundle"]

    def postprocess_review_flags(self, bean: CoffeeBean, url: str) -> CoffeeBean:
        if not url:
            return bean
        url_lower = str(url).lower()
        if "4_bundle" in url_lower or "bundle" in url_lower:
            bean.is_tasting_kit = True
        return bean

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from a WooCommerce category page.

        WooCommerce product permalinks here are `/shop/<category>/<product-slug>/`.
        Sold-out variable products are flagged with text within the product card.
        """
        soup = await self.fetch_page(store_url, use_playwright=False)
        if not soup:
            if store_url not in self._failed_listing_urls:
                self._failed_listing_urls.append(store_url)
            return []

        product_urls: list[str] = []
        for card in soup.select(".product_item"):
            card_text = card.get_text(" ", strip=True).lower()
            if any(marker in card_text for marker in ("out of stock", "sold out", "unavailable")):
                continue

            link = card.find("a", href=True)
            if not isinstance(link, Tag):
                continue
            href = str(link.get("href"))
            # Only accept true product permalinks: /shop/<category>/<slug>/
            if not re.search(r"/shop/[^/]+/[^/]+/?$", href):
                continue

            full_url = self.resolve_url(href)
            # Coffee determination happens on the card's display name, not the URL.
            # We crawl only coffee-only category pages (espresso/filter/bundles), so the
            # URL-level is_coffee_product_url guard is unnecessary here - and its global
            # "ticket" exclusion would wrongly drop the "Golden Ticket" coffee.
            if not self.is_coffee_product_name(card_text):
                continue
            product_urls.append(full_url)
            logger.debug(f"Including product URL: {full_url}")

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_urls = []
        for url in product_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        logger.info(f"Found {len(unique_urls)} coffee product URLs from {store_url}")
        return unique_urls
