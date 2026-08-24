"""Grain and Grind scraper implementation with AI extraction (WooCommerce).

Grain and Grind (grainandgrind.co.uk) is a WordPress + WooCommerce roastery
and coffee-shop chain based in Inverness, Scotland (with shops across
Scotland, including Glasgow). The WooCommerce Store API is not used;
discovery and extraction run off server-rendered HTML per the non-Shopify
skill.

Coffee products live under ``/product-category/coffee/`` (all beans, blends
and decaf) which is paginated (``nav.woocommerce-pagination``, currently 3
pages / 30 products). Product pages are at ``/product/<slug>/`` and render
each product inside a single ``div.product`` container (title, price, short
description, add-to-cart), which we send to the AI for token savings.

Genuine non-coffee products (brewing equipment, brew bags, merch,
subscriptions, gift vouchers) live under separate categories
(``/product-category/equipment-shop/``, ``brew-bags/``, ``coffee-merch/``,
``subscriptions/``) that we never crawl; the ``/product/`` required path
pattern plus the exclude slugs keep any stragglers out. Tasting-kit/sampler
tokens are NOT excluded - they flow through and get flagged for review.
"""

import logging

from bs4 import BeautifulSoup

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="grain-and-grind",
    display_name="Grain and Grind",
    roaster_name="Grain and Grind",
    website="https://grainandgrind.co.uk",
    description=(
        "Scottish coffee roastery and coffee-shop chain based in Inverness, "
        "with shops across Scotland including Glasgow (WooCommerce). Roasts "
        "single origins, blends and decaf."
    ),
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class GrainAndGrindScraper(BaseScraper):
    """Scraper for Grain and Grind (grainandgrind.co.uk) with AI extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize the Grain and Grind scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Grain and Grind",
            base_url="https://grainandgrind.co.uk",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

        # Genuine non-coffee products (equipment, brew bags, merch,
        # subscriptions, gift vouchers). NOTE: tasting-kit tokens are
        # intentionally NOT listed here - any sampler/kit products flow
        # through and get flagged for review.
        self.exclude_slugs = [
            "equipment",
            "brew-bag",
            "merch",
            "subscription",
            "gift",
            "voucher",
            "aeropress",
        ]

    async def get_store_urls(self) -> list[str]:
        """Get the coffee category listing URL to crawl.

        /product-category/coffee/ lists every coffee product as a WooCommerce
        card and is paginated; pagination pages are followed dynamically in
        ``_extract_product_urls_from_store``.
        """
        return [
            "https://grainandgrind.co.uk/product-category/coffee/",
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

        WooCommerce renders each product inside a single ``div.product``
        section (title, price, short description, add-to-cart), which is a
        few KB vs the ~150 KB page. We send only that to the AI to keep token
        usage down. Listing/category pages are left intact so card extraction
        still works.
        """
        soup = await super().fetch_page(*args, **kwargs)
        url = kwargs.get("url") or (args[0] if args else "")
        if not soup or "/product/" not in url:
            return soup

        product_container = soup.select_one("div.product")
        if product_container is None:
            return soup
        logger.debug(f"Pruned product page to div.product for {url}")
        wrapper = BeautifulSoup("<html><head></head><body></body></html>", "html.parser")
        wrapper.body.append(product_container)
        return wrapper

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from the WooCommerce coffee category page.

        # Sold-out detection: class-based on the li.product card
        Each product card is a ``li.product``; sold-out items carry an
        ``outofstock`` / ``sold-out`` / ``oos`` class (no price shown). We
        check the card class list BEFORE URL filtering so excluded products
        never leak past the stock check.

        Follows ``nav.woocommerce-pagination`` (``a.next.page-numbers``) so
        the number of category pages is discovered dynamically rather than
        hardcoded.
        """
        all_product_urls = []
        page_url = store_url

        while page_url:
            soup = await self.fetch_page(page_url, use_playwright=False)
            if not soup:
                break

            for card in soup.select("li.product"):
                card_classes = " ".join(card.get("class", []))
                if any(token in card_classes for token in ("outofstock", "sold-out", "oos")):
                    logger.debug(f"Skipping sold-out card: {card_classes}")
                    continue
                link = card.select_one('a[href*="/product/"]') or card.select_one(".woocommerce-loop-product__link")
                if not link:
                    continue
                href = link.get("href")
                if not href:
                    continue
                all_product_urls.append(self.resolve_url(href))

            next_link = soup.select_one("a.next.page-numbers")
            if not next_link or not next_link.get("href"):
                break
            next_url = self.resolve_url(next_link["href"])
            if next_url == page_url:
                break
            page_url = next_url

        # Filter non-coffee products using base class logic and the required
        # /product/ path pattern (keeps equipment/brew-bags/merch out).
        filtered_urls = []
        for url in all_product_urls:
            if not url:
                continue
            # Never drop sampler/kit products; only genuine non-coffee slugs.
            if any(slug in url.lower() for slug in self.exclude_slugs):
                logger.debug(f"Skipping excluded product slug: {url}")
                continue
            if self.is_coffee_product_url(url, required_path_patterns=["/product/"]):
                filtered_urls.append(url)

        filtered_urls = list(dict.fromkeys(filtered_urls))
        logger.info(f"Found {len(filtered_urls)} available product URLs from {store_url}")
        return filtered_urls
