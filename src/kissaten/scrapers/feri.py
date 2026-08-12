"""Feri (feripoint.com) scraper implementation with AI-powered extraction (WooCommerce)."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="feri",
    display_name="Feri",
    roaster_name="Feri",
    website="https://feripoint.com",
    description="Specialty coffee roaster based in the United Kingdom (WooCommerce).",
    requires_api_key=True,
    currency="GBP",  # UK Pound
    country="United Kingdom",
    status="available",
)
class FeriScraper(BaseScraper):
    """Scraper for Feri (feripoint.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Feri scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Feri",
            base_url="https://feripoint.com",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape (WooCommerce shop and discovery collection)."""
        return [
            "https://feripoint.com/shop/",
            "https://feripoint.com/shop/page/2/",
            "https://feripoint.com/discovery-collection/",
        ]

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction."""
        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=False,
            use_optimized_mode=False,
        )

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from a WooCommerce store/collection page.

        Feri runs a modern WooCommerce runtime (wc-block-product-template), so
        each product is a `<li class="wc-block-product ...">` card. Sold-out
        items are flagged on the card itself via the ``outofstock`` status
        class (WooCommerce Blocks) and/or an "Out of stock"/"Sold out" badge
        (classic WooCommerce themes).

        # Sold-out detection: card-level "Out of stock"/"Sold out" text or `outofstock` class
        Sold-out filtering runs BEFORE is_coffee_product_url so sold-out items
        never leak past the stock check. Checks are scoped to the individual
        product card (never a whole-page text search) so marketing blurbs such
        as "Once sold out, they will not return" on the discovery collection
        page do not cause false positives.
        """
        soup = await self.fetch_page(store_url, use_playwright=False)
        if not soup:
            return []

        # Product card containers used by WooCommerce Blocks and classic themes.
        cards = soup.select(
            "li.wc-block-product, "
            "li.product, "
            "li.type-product, "
            "div.product, "
            "div.wc-block-grid__product"
        )
        product_urls = []
        for card in cards:
            card_text = card.get_text(" ", strip=True)
            card_classes = " ".join(card.get("class") or []).lower()
            if "Out of stock" in card_text or "Sold out" in card_text:
                continue
            if any(token in card_classes for token in ("outofstock", "sold-out", "out-of-stock")):
                continue
            link = card.select_one('a[href*="/product/"]')
            if not link:
                continue
            href = link.get("href")
            if not href:
                continue
            url = self.resolve_url(href)
            if self.is_coffee_product_url(url, required_path_patterns=["/product/"]):
                product_urls.append(url)

        # Fallback: some store pages (e.g. the Elementor-driven discovery
        # collection) link products from marketing blocks that are not wrapped
        # in a WooCommerce product card. Only take /product/ links here and
        # still apply is_coffee_product_url for coffee filtering; sold-out
        # filtering is card-scoped above and intentionally not a page-wide
        # text search.
        if not product_urls:
            for link in soup.select('a[href*="/product/"]'):
                href = link.get("href")
                if not href:
                    continue
                url = self.resolve_url(href)
                if self.is_coffee_product_url(url, required_path_patterns=["/product/"]):
                    product_urls.append(url)

        # Remove duplicates while preserving order.
        seen = set()
        unique_urls = []
        for url in product_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        logger.info(f"Found {len(unique_urls)} available product URLs from {store_url}")
        return unique_urls
