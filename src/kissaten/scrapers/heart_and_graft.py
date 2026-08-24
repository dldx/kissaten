"""Heart & Graft Coffee Roasters scraper with AI extraction (WooCommerce).

Heart & Graft (heartandgraft.co.uk) is a WordPress + WooCommerce storefront
(Shopkeeper theme) in Manchester, UK. Discovery and extraction run off the
server-rendered HTML.

The ``/shop/coffee/`` page lists every coffee product as a WooCommerce
``li.product`` card (house blends, house singles, single origins) alongside
the recurring ``*-subscription`` cards. We crawl ``/shop/coffee/`` plus the
three coffee subcategories (house-blends, house-singles, single-origin) for
resilience and deduplicate, so a product promoted to a subcategory is not lost.

The ``discovery-box`` product is a curated coffee sampler box, NOT a
subscription — we retain it (the base ``_apply_product_flags`` flags any kit it
finds for admin review). Genuine non-coffee products to exclude are the
``*-subscription`` coffee plans (``roasters-choice-subscription``,
``espresso-blend-coffee-subscription``, etc.). Brewing equipment and
merch-and-curios live on separate category paths (``/shop/brewing-equipment/``,
``/shop/merch-and-curios/``) that we never crawl, so equipment/merch never
leak in.

Sold-out detection: class-based on the ``li.product`` card (the WooCommerce
``outofstock`` / ``sold-out`` / ``oos`` status classes and the Shopkeeper
``out_of_stock_badge_loop`` badge class), before URL filtering.
"""

import logging

from bs4 import BeautifulSoup

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="heart-and-graft",
    display_name="Heart & Graft",
    roaster_name="Heart & Graft",
    website="https://heartandgraft.co.uk",
    description=(
        "Specialty coffee roaster based in Manchester, UK (WooCommerce). "
        "Roasts house blends, house singles and single origins in-house."
    ),
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class HeartAndGraftScraper(BaseScraper):
    """Scraper for Heart & Graft (heartandgraft.co.uk) with AI extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize the Heart & Graft scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Heart & Graft",
            base_url="https://heartandgraft.co.uk",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

        # Genuine non-coffee products (recurring subscription plans).
        # NOTE: tasting-kit/sampler tokens (e.g. "discovery-box") are
        # intentionally NOT listed here - any kit flows through and gets
        # flagged for review. Equipment/merch never appear because we only
        # crawl the coffee category paths.
        self.exclude_slugs = [
            "subscription",
        ]

    async def get_store_urls(self) -> list[str]:
        """Get the coffee category listing URLs to crawl.

        /shop/coffee/ lists all coffee products; we also crawl the three
        coffee subcategories so a product promoted to a subcategory is not
        missed, and deduplicate across them.
        """
        return [
            "https://heartandgraft.co.uk/shop/coffee/",
            "https://heartandgraft.co.uk/shop/coffee/house-blends/",
            "https://heartandgraft.co.uk/shop/coffee/house-singles/",
            "https://heartandgraft.co.uk/shop/coffee/single-origin/",
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

        The Shopkeeper theme renders each product inside a single ``div.product``
        section (title, price, description, add-to-cart). We send only that to
        the AI to keep token usage down. Listing/category pages (the bare
        ``/shop/coffee/...`` index pages) are left intact so card extraction
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
        """Extract product URLs from a WooCommerce coffee category page.

        # Sold-out detection: class-based on the li.product card
        Each product card is a ``li.product``; sold-out items carry the
        WooCommerce ``outofstock`` / ``sold-out`` / ``oos`` status class or the
        Shopkeeper ``out_of_stock_badge_loop`` badge class (no price shown). We
        check the card class list BEFORE URL filtering so excluded products
        never leak past the stock check.
        """
        soup = await self.fetch_page(store_url, use_playwright=False)
        if not soup:
            return []

        all_product_urls = []
        for card in soup.select("li.product"):
            card_classes = " ".join(card.get("class", []))
            if any(token in card_classes for token in ("outofstock", "sold-out", "oos", "out_of_stock")):
                logger.debug(f"Skipping sold-out card: {card_classes}")
                continue
            link = card.select_one('a[href*="/product/"]')
            if not link:
                continue
            href = link.get("href")
            if not href:
                continue
            all_product_urls.append(self.resolve_url(href))

        # Filter non-coffee products: require the /product/ path and exclude
        # genuine subscription plans only. We use explicit slug matching here
        # (not the base-class default excluded-pattern list) so coffee
        # samplers like "discovery-box" are retained rather than dropped.
        filtered_urls = []
        for url in all_product_urls:
            if not url:
                continue
            if any(slug in url.lower() for slug in self.exclude_slugs):
                logger.debug(f"Skipping excluded product slug: {url}")
                continue
            if "/product/" not in url.lower():
                continue
            filtered_urls.append(url)

        filtered_urls = list(dict.fromkeys(filtered_urls))
        logger.info(f"Found {len(filtered_urls)} available product URLs from {store_url}")
        return filtered_urls
