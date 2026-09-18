"""Ief & Ido scraper implementation with AI-powered extraction (WooCommerce).

Ief & Ido (iefido.nl) is a specialty coffee roastery in Den Haag, Netherlands,
running WordPress + WooCommerce. Platform notes from curl-first discovery:

- ``<meta name="generator" content="WooCommerce 11.1.0">`` -> WooCommerce.
- Coffee catalogue: ``/product-categorie/coffee/`` (~19 products, single page —
  no WooCommerce pagination links present).
- Product URLs: ``/product/<slug>/``; out-of-stock items carry the
  ``outofstock`` class on the ``li.product`` card and an "Out of Stock" badge.
- Product pages are fully server-rendered inside the theme's ``div.product``
  container (name, variations, € prices, English tasting-note copy).
"""

import logging

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)

# Card-level sold-out markers (English "Out of Stock" badge; Dutch variants
# kept for safety in case the theme locale changes).
_SOLD_OUT_MARKERS = ("out of stock", "uitverkocht", "niet op voorraad")


@register_scraper(
    name="ief-ido",
    display_name="Ief & Ido",
    roaster_name="Ief & Ido",
    website="https://iefido.nl",
    description="Specialty coffee roastery in Den Haag, Netherlands (WooCommerce).",
    requires_api_key=True,
    currency="EUR",
    country="Netherlands",
    status="experimental",
)
class IefIdoScraper(BaseScraper):
    """Scraper for Ief & Ido (iefido.nl) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize the Ief & Ido scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Ief & Ido",
            base_url="https://iefido.nl",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = None
        try:
            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
        except ValueError:
            logger.warning("Google API key not configured. AI extraction will not be available.")

    async def get_store_urls(self) -> list[str]:
        """Get the coffee category URL.

        Returns:
            List containing the WooCommerce coffee category URL.
        """
        return ["https://iefido.nl/product-categorie/coffee/"]

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page, narrowing WooCommerce product detail pages to the product container.

        WooCommerce themes wrap the whole product detail (title, variations,
        prices, description, meta) in a ``div.product`` element. Narrowing the
        soup to that container strips header/footer/analytics markup before the
        HTML reaches the AI extractor.

        Args:
            *args: Positional arguments forwarded to the base fetch_page.
            **kwargs: Keyword arguments forwarded to the base fetch_page.

        Returns:
            BeautifulSoup object (narrowed for product pages) or None if the fetch failed.
        """
        soup = await super().fetch_page(*args, **kwargs)
        url = kwargs.get("url") or (args[0] if args else "")
        if soup is None or "/product/" not in (url or ""):
            return soup

        product_el = soup.select("div.product")
        if len(product_el) == 1:
            logger.debug(f"Narrowed soup to div.product for {url}")
            return product_el[0]
        logger.warning(f"Expected 1 div.product for {url}, found {len(product_el)}")
        return soup

    # Sold-out detection: WooCommerce card class + card text.
    # Out-of-stock ``li.product`` cards carry the ``outofstock`` class and an
    # "Out of Stock" badge; the text check runs on the individual card element
    # (never the whole page, where theme CSS/JS strings would false-positive).
    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract in-stock coffee product URLs from the WooCommerce category page.

        Args:
            store_url: URL of the coffee category page.

        Returns:
            List of in-stock product URLs.
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        product_urls: list[str] = []
        seen: set[str] = set()

        for card in soup.select("li.product"):
            link = card.select_one("a[href*='/product/']")
            if not link:
                continue
            href = link.get("href")
            if not href or not isinstance(href, str):
                continue

            full_url = self.resolve_url(href.split("?")[0].split("#")[0])

            classes = " ".join(card.get("class") or []).lower()
            card_text = card.get_text(" ", strip=True).lower()
            if "outofstock" in classes or any(marker in card_text for marker in _SOLD_OUT_MARKERS):
                logger.debug(f"Skipping sold-out product: {full_url}")
                continue

            if not self.is_coffee_product_url(full_url, required_path_patterns=["/product/"]):
                continue

            if full_url not in seen:
                seen.add(full_url)
                product_urls.append(full_url)

        logger.info(f"Found {len(product_urls)} in-stock coffee product URLs from {store_url}")
        return product_urls

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction.

        Args:
            product_urls: List of URLs for new products.

        Returns:
            List of newly scraped CoffeeBean objects.
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
            # Product copy is written in English (Dutch only in site chrome).
            translate_to_english=False,
        )

    def postprocess_review_flags(self, bean: CoffeeBean, url: str) -> CoffeeBean:
        """Flag Ief & Ido tasting packages / Fermentation Project kits for review."""
        haystack = f"{url} {getattr(bean, 'name', '') or ''}".lower()
        if "proefpakket" in haystack or "tasting package" in haystack or "fermentation-project" in haystack:
            bean.is_tasting_kit = True
        return bean

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Pin the store currency (the registry lookup by display name can fall back to GBP)."""
        bean.currency = "EUR"
        return bean
