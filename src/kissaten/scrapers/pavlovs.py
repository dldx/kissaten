"""Pavlov's Coffee scraper implementation with AI-powered extraction (WooCommerce)."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="pavlovs",
    display_name="Pavlov's Coffee",
    roaster_name="Pavlov's Coffee",
    website="https://pavlovscoffee.co.za",
    description="Micro-batch roaster of single-origin (often organic) coffee in Cape Town, South Africa (WooCommerce).",
    requires_api_key=True,
    currency="ZAR",  # South African Rand
    country="South Africa",
    status="available",
)
class PavlovsScraper(BaseScraper):
    """Scraper for Pavlov's Coffee (pavlovscoffee.co.za) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Pavlov's scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Pavlov's Coffee",
            base_url="https://pavlovscoffee.co.za",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape (shop archive and coffee product category)."""
        return [
            "https://pavlovscoffee.co.za/shop/",
            "https://pavlovscoffee.co.za/product-category/coffee/",
        ]

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction.

        Args:
            product_urls: List of URLs for new products

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
        """Pin the currency to ZAR as a final guard."""
        bean.currency = "ZAR"
        return bean

    def _find_product_card(self, link_element):
        """Find the WooCommerce product card (closest ``<li>`` ancestor)."""
        card = link_element.find_parent("li")
        if card is not None:
            return card
        return link_element.parent

    def _is_sold_out(self, link_element) -> bool:
        """Check whether a product card is marked sold out."""
        card = self._find_product_card(link_element)
        if card is None:
            return False
        # Class-based detection (WooCommerce adds `outofstock` to the card <li>).
        for node in [card, *card.parents]:
            if not hasattr(node, "get"):
                break
            classes = node.get("class") or []
            if isinstance(classes, str):
                classes = [classes]
            for cls in classes:
                cls_lower = cls.lower().replace("-", "").replace("_", "")
                if "outofstock" in cls_lower or "soldout" in cls_lower:
                    return True
        # Text-based detection on the card only (never the whole page — the
        # strings otherwise appear inside embedded JSON/JS payloads).
        text = card.get_text(" ", strip=True).lower()
        return "out of stock" in text or "sold out" in text

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from a store/category page.

        Product pages live under ``/shop/<slug>/``. Pagination is walked via
        ``/page/N/`` until a page yields no products (a 404 archive page has
        no product loop).

        Args:
            store_url: URL of the store page

        Returns:
            List of product URLs
        """
        # Sold-out detection: WooCommerce `outofstock` class on the product
        # card <li> plus "Out of stock"/"Sold out" text within the card.
        all_product_urls: list[str] = []
        base = store_url.rstrip("/")
        for page_num in range(1, 21):  # safety cap
            page_url = store_url if page_num == 1 else f"{base}/page/{page_num}/"
            soup = await self.fetch_page(page_url, use_playwright=False)
            if not soup:
                break

            link_elements = soup.select("a.woocommerce-LoopProduct-link, a.woocommerce-loop-product__link")
            if not link_elements:
                link_elements = soup.select("li.product a[href]")
            if not link_elements:
                break

            page_urls: list[str] = []
            for el in link_elements:
                if self._is_sold_out(el):
                    logger.debug("Skipping sold-out product card")
                    continue
                href = el.get("href")
                if not href or not isinstance(href, str):
                    continue
                full_url = self.resolve_url(href)
                # Product pages are /shop/<slug>/; category archives (e.g.
                # /product-category/coffee/) live elsewhere and RSS feeds at
                # /shop/feed/ must not leak in.
                if "/feed" in full_url:
                    continue
                if full_url.rstrip("/").endswith("/shop"):
                    continue
                if self.is_coffee_product_url(full_url, required_path_patterns=["/shop/"]):
                    page_urls.append(full_url)

            if not page_urls:
                break
            all_product_urls.extend(page_urls)

            # Only continue if the page itself links to the next archive page;
            # this avoids blind 404 fetches at the end of pagination.
            if f"/page/{page_num + 1}/" not in page_url and not any(
                f"/page/{page_num + 1}/" in (a.get("href") or "") for a in soup.select("a[href*='/page/']")
            ):
                break

        # Filter out non-coffee items (subscriptions, gift cards, merch).
        excluded_products = [
            "subscription",
            "gift",
            "giftcard",
            "merch",
            "equipment",
        ]
        filtered_urls = [
            url
            for url in all_product_urls
            if url and isinstance(url, str) and not any(ex in url.lower() for ex in excluded_products)
        ]

        logger.info(f"Found {len(filtered_urls)} available product URLs from {store_url}")
        return list(dict.fromkeys(filtered_urls))
