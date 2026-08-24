"""Duffin's Coffee Roaster scraper implementation with AI extraction (WooCommerce).

Duffin's (duffinscoffee.com) is a WordPress + WooCommerce + Elementor
storefront in Staveley, Kendal (Lake District, UK). The roaster rebranded
from "Mr Duffins Coffee" to "Duffin's" (the ``.co.uk``/``mrduffinscoffee.com``
domains are dead). The wp-json REST API responds 200 but we scrape the
server-rendered HTML per the non-Shopify skill.

Coffee products live under ``/shop/coffee/<slug>/`` (e.g.
``/shop/coffee/chin-wag-coffee-blend/``). The ``/shop/`` index lists all
products as WooCommerce ``li.product`` cards, including duplicated
"featured/related" cards and two stale pagination links (``/shop/page/2/``
returns the same 19 cards), so we crawl only ``/shop/`` and deduplicate.

Two product cards (Juicy Gossip, Chit Chat) link to a taxonomy archive URL
``/shop/type/<taxonomy>/<slug>/`` rather than the canonical product page; we
normalise those back to ``/shop/coffee/<slug>/`` (both resolve 200 to the same
product).

Genuine non-coffee products to exclude are gift cards / gift sets / gift
hampers (``duffins-gift-card``, ``ugandan-gift-set-...``, ``*-hamper``).
Equipment, hot-chocolate and tea live on separate category paths
(``/shop/equipment/``, ``/shop/hot-chocolate/``, ``/shop/tea/``) that we never
crawl, and the ``/shop/coffee/`` required path pattern keeps any stragglers
out. Tasting-kit/sampler tokens are NOT excluded.

Sold-out detection: class-based on the ``li.product`` card (the
``outofstock`` / ``sold-out`` / ``oos`` classes), before URL filtering.
"""

import logging

from bs4 import BeautifulSoup

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="duffins",
    display_name="Duffin's",
    roaster_name="Duffin's",
    website="https://duffinscoffee.com",
    description=(
        "Independent specialty coffee roaster based in Staveley, Kendal, Lake "
        "District (WooCommerce + Elementor). Roasts blends and single origins "
        "in-house on a 15kg Giesen roaster."
    ),
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class DuffinsScraper(BaseScraper):
    """Scraper for Duffin's Coffee Roaster (duffinscoffee.com) with AI extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize the Duffin's scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Duffin's",
            base_url="https://duffinscoffee.com",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

        # Genuine non-coffee products (gift cards / gift sets / gift hampers).
        # NOTE: tasting-kit tokens are intentionally NOT listed here - any
        # sampler/kit products flow through and get flagged for review.
        self.exclude_slugs = [
            "gift",
            "hamper",
        ]

    async def get_store_urls(self) -> list[str]:
        """Get the shop index URL to crawl.

        /shop/ lists every coffee product as a WooCommerce card. /shop/page/2/
        returns an identical 19-card listing (stale pagination), so we only
        crawl /shop/ and deduplicate the featured/related duplicate cards.
        """
        return [
            "https://duffinscoffee.com/shop/",
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
        """Pin GBP as the store currency (final guard)."""
        bean.currency = "GBP"
        return bean

    async def fetch_page(self, *args, **kwargs):
        """Narrow product pages to the WooCommerce ``div.product`` container.

        Elementor renders each product inside a single ``div.product`` section
        (title, price, short description, add-to-cart), which is ~1 KB vs the
        ~110 KB page. We send only that to the AI to keep token usage down.
        Listing/category pages (the bare ``/shop/`` index) are left intact so
        card extraction still works.
        """
        soup = await super().fetch_page(*args, **kwargs)
        url = kwargs.get("url") or (args[0] if args else "")
        if not soup or ("/shop/coffee/" not in url and "/shop/type/" not in url):
            return soup

        product_container = soup.select_one("div.product")
        if product_container is None:
            return soup
        logger.debug(f"Pruned product page to div.product for {url}")
        wrapper = BeautifulSoup("<html><head></head><body></body></html>", "html.parser")
        wrapper.body.append(product_container)
        return wrapper

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from the WooCommerce shop index page.

        # Sold-out detection: class-based on the li.product card
        Each product card is a ``li.product``; sold-out items carry an
        ``outofstock`` / ``sold-out`` / ``oos`` class (no price shown). We
        check the card class list BEFORE URL filtering so excluded products
        never leak past the stock check.
        """
        soup = await self.fetch_page(store_url, use_playwright=False)
        if not soup:
            return []

        all_product_urls = []
        for card in soup.select("li.product"):
            card_classes = " ".join(card.get("class", []))
            if any(token in card_classes for token in ("outofstock", "sold-out", "oos")):
                logger.debug(f"Skipping sold-out card: {card_classes}")
                continue
            link = card.select_one('a[href*="/shop/"]')
            if not link:
                continue
            href = link.get("href")
            if not href:
                continue
            href = self.resolve_url(href)
            # Normalise taxonomy archive links to the canonical product URL.
            # /shop/type/<taxonomy>/<slug>/ -> /shop/coffee/<slug>/
            if "/shop/type/" in href:
                slug = href.rstrip("/").split("/")[-1]
                href = f"{self.base_url}/shop/coffee/{slug}/"
            all_product_urls.append(href)

        # Filter non-coffee products using base class logic and the required
        # /shop/coffee/ path pattern (keeps equipment/tea/hot-chocolate out).
        filtered_urls = []
        for url in all_product_urls:
            if not url:
                continue
            # Never drop sampler/kit products; only genuine non-coffee slugs.
            if any(slug in url.lower() for slug in self.exclude_slugs):
                logger.debug(f"Skipping excluded product slug: {url}")
                continue
            if self.is_coffee_product_url(url, required_path_patterns=["/shop/coffee/"]):
                filtered_urls.append(url)

        filtered_urls = list(dict.fromkeys(filtered_urls))
        logger.info(f"Found {len(filtered_urls)} available product URLs from {store_url}")
        return filtered_urls
