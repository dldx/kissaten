"""The Underdog scraper implementation with AI-powered extraction (WooCommerce)."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="the-underdog",
    display_name="The Underdog",
    roaster_name="The Underdog",
    website="https://www.underdog.gr",
    description="Specialty coffee roaster based in Athens, Greece (WooCommerce).",
    requires_api_key=True,
    currency="EUR",  # Euro
    country="Greece",
    status="available",
)
class TheUnderdogScraper(BaseScraper):
    """Scraper for The Underdog (underdog.gr) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize The Underdog scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="The Underdog",
            base_url="https://www.underdog.gr",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape (espresso and filter categories)."""
        return [
            "https://www.underdog.gr/shop/category/espresso/",
            "https://www.underdog.gr/shop/category/filter-coffee/",
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

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        bean.currency = "EUR"
        return bean

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from category page.

        WooCommerce typically uses `/product/` URLs and marks out-of-stock items
        with badges or text like "Out of stock". We'll filter those out.
        """
        soup = await self.fetch_page(store_url, use_playwright=False)
        if not soup:
            return []

        all_product_urls = []
        # Common WooCommerce selectors
        # WooCommerce common product link selector
        link_elements = soup.select('a.woocommerce-LoopProduct-link, a[href*="/product/"]')
        for el in link_elements:
            parent_text = el.parent.parent.text if el.parent and el.parent.parent else ""
            text = (parent_text or "") + (el.text or "")
            # Exclude out of stock products
            if "Out of stock" in text or "Sold out" in text:
                continue
            href = el.get("href")
            if href:
                all_product_urls.append(href)

        # Filter non-coffee items by simple heuristics
        excluded_products = [
            "subscription",
            "gift",
            "giftcard",
            "merch",
            "equipment",
            "brew",
            "sample-box",
        ]

        filtered_urls = []
        for url in all_product_urls:
            if url and isinstance(url, str) and not any(ex in url.lower() for ex in excluded_products):
                filtered_urls.append(url)

        logger.info(f"Found {len(filtered_urls)} available product URLs from {store_url}")
        return list(set(filtered_urls))
