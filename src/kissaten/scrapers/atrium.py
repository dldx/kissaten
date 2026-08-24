"""Atrium Coffee Roasters scraper implementation with AI-powered extraction.

Atrium Coffee Roasters (atriumcoffeeroasters.com, Manchester) runs a
WooCommerce/Divi shop. The original checklist domain atriumcoffee.co.uk is an
unconnected Wix error; the live WooCommerce store is atriumcoffeeroasters.com.

The store's nav exposes /product-category/coffee/, single-origin/, decaf/,
blends/, espresso/, gold-leaf-series/, merchandise/ and club/. The coffee and
single-origin categories between them carry the full current coffee catalogue;
merchandise (sticker sets) and club (subscriptions) are genuine excludes. The
decaf/, blends/ and espresso/ archive pages currently render zero product
cards, so they are not crawled (an empty listing page would be recorded as a
failed listing and suppress out-of-stock updates).

Sold-out detection: card-level text on the WooCommerce ``li.product`` card
before URL coalescing ("Out of stock").
"""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="atrium",
    display_name="Atrium Coffee Roasters",
    roaster_name="Atrium Coffee Roasters",
    website="https://atriumcoffeeroasters.com",
    description="Specialty coffee roaster based in Manchester, UK. "
    "WooCommerce storefront (Divi theme) with curated single-origin, "
    "espresso and blend coffees.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class AtriumScraper(BaseScraper):
    """Scraper for Atrium Coffee Roasters (atriumcoffeeroasters.com) with AI extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Atrium Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Atrium Coffee Roasters",
            base_url="https://atriumcoffeeroasters.com",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get the category URLs to crawl (full coffee catalogue)."""
        return [
            "https://atriumcoffeeroasters.com/product-category/coffee/",
            "https://atriumcoffeeroasters.com/product-category/single-origin/",
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
        # WooCommerce Payments presents a geo-localized currency (USD here);
        # pin to the roaster's home currency.
        bean.currency = "GBP"
        return bean

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from a WooCommerce category page.

        # Sold-out detection: card-level text detection on li.product
        Cards are ``li.product`` anchors; sold-out items carry an "Out of
        stock" badge in the card text, so filter the card text BEFORE URL
        filtering to keep excluded product leakage out.
        """
        soup = await self.fetch_page(store_url, use_playwright=False)
        if not soup:
            return []

        all_product_urls = []
        for card in soup.select("li.product"):
            card_text = card.get_text(" ", strip=True)
            if "Out of stock" in card_text or "Sold out" in card_text or "Unavailable" in card_text:
                continue
            link = card.select_one('a[href*="/product/"]')
            if link:
                href = link.get("href")
                if href:
                    all_product_urls.append(href)

        # Filter non-coffee products using base class logic and required path pattern.
        filtered_urls = []
        for url in all_product_urls:
            if url and self.is_coffee_product_url(url, required_path_patterns=["/product/"]):
                filtered_urls.append(url)

        logger.info(f"Found {len(filtered_urls)} available product URLs from {store_url}")
        return list(dict.fromkeys(filtered_urls))
