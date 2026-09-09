"""Simple Bru Coffee Co scraper implementation with AI-powered extraction (WooCommerce)."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="simple-bru",
    display_name="Simple Bru Coffee Co",
    roaster_name="Simple Bru Coffee Co",
    website="https://simplebrucoffee.co.za",
    description="Specialty coffee roaster and coffee shops in Cape Town, South Africa "
    "(WooCommerce with WordPress default `?product=` permalinks).",
    requires_api_key=True,
    currency="ZAR",  # South African Rand
    country="South Africa",
    status="available",
)
class SimpleBruScraper(BaseScraper):
    """Scraper for Simple Bru Coffee Co (simplebrucoffee.co.za) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Simple Bru scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Simple Bru Coffee Co",
            base_url="https://simplebrucoffee.co.za",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        The site runs WordPress with default (non-pretty) permalinks, so the
        WooCommerce shop archive lives at ``/?page_id=1400`` (the "Shop"
        page); ``/shop/`` itself returns a 404. Product pages use the
        ``?product=<slug>`` query-string permalink format.
        """
        return ["https://simplebrucoffee.co.za/?page_id=1400"]

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
        for node in card.parents:
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
        """Extract product URLs from the shop page.

        Args:
            store_url: URL of the store page

        Returns:
            List of product URLs
        """
        # Sold-out detection: WooCommerce `outofstock` class on the product
        # card <li> plus "Out of stock"/"Sold out" text within the card.
        soup = await self.fetch_page(store_url, use_playwright=False)
        if not soup:
            return []

        # The shop page uses an Elementor product grid whose links carry the
        # standard WooCommerce loop-link classes.
        link_elements = soup.select("a.woocommerce-LoopProduct-link, a.woocommerce-loop-product__link")
        if not link_elements:
            link_elements = soup.select("li.product a[href]")

        # Products use `?product=<slug>` permalinks (ugly WordPress permalinks).
        product_urls: list[str] = []
        for el in link_elements:
            if self._is_sold_out(el):
                logger.debug("Skipping sold-out product card")
                continue
            href = el.get("href")
            if not href or not isinstance(href, str):
                continue
            full_url = self.resolve_url(href)
            if self.is_coffee_product_url(full_url, required_path_patterns=["?product="]):
                product_urls.append(full_url)

        # Filter out non-coffee items (subscriptions, merch, gift cards, etc.)
        # — the base class exclusions cover most of these already.
        excluded_products = [
            "subscription",
            "gift",
            "giftcard",
            "merch",
            "equipment",
        ]
        filtered_urls = [
            url
            for url in product_urls
            if url and isinstance(url, str) and not any(ex in url.lower() for ex in excluded_products)
        ]

        logger.info(f"Found {len(filtered_urls)} available product URLs from {store_url}")
        return list(dict.fromkeys(filtered_urls))
