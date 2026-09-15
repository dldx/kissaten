"""Massimo Coffee scraper implementation with AI-powered extraction (Ecwid Instant Site).

Massimo Coffee Roasters (icoffee.store) roasts in Almaty and ships across
Kazakhstan ("Свежеобжаренный кофе в Алматы" / "Доставка по Алматы и всему
Казахстану"). The storefront runs on Ecwid's Instant Site platform
(``<meta name="generator" content="ec-instant-site">``), not Shopify.

Platform notes from curl-first discovery (2026-09):
- ``/products.json`` is not available (Ecwid) -> the category page is used.
- ``https://icoffee.store/products/`` is server-rendered: every product is a
  ``div.grid-product`` card containing an anchor to ``/products/<slug>``, the
  price in Kazakhstani tenge ("KZT 9 350") and a sold-out label when applicable.
- Product detail pages are also server-rendered. All useful content (title,
  price, grind options, stock status, full description) lives inside the stable
  ``div.static-product-browser`` container, so ``fetch_page`` narrows the soup
  to it — a large token saving with no information loss. The ``application/ld+json``
  Product/Offer block sits outside that container but is not needed: the visible
  text already carries the price and stock status.
- The catalogue is in Russian, so ``translate_to_english=True``.
- The store currency is KZT (both the visible "KZT 9 350" labels and the
  JSON-LD ``priceCurrency: KZT`` offer agree).
"""

import logging

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)

# Non-product Ecwid "pages" that live under /products/ but are categories.
_CATEGORY_SLUGS = {"kofe", "espresso", "drip-kofe", "osnaschenie", "filtr", "merch"}

# Russian-language equipment/merch slugs the base exclusion list does not cover
# (grinder = kofemolka, handle = ruchka, tuning kit = tyuning, t-shirt = futbolka,
# mug = kruzhka, cup = chashka, glass = stakanchik, spoon = lozhka, tote = shopper).
_EXTRA_EXCLUDED_SLUGS = (
    "kofemolka",
    "espro",
    "ruchka",
    "tyuning",
    "futbolka",
    "kruzhka",
    "chashka",
    "stakanchik",
    "lozhka",
    "shopper",
)


@register_scraper(
    name="massimo-coffee",
    display_name="Massimo Coffee",
    roaster_name="Massimo Coffee",
    website="https://icoffee.store",
    description=(
        "Coffee roaster in Almaty, Kazakhstan, running an Ecwid Instant Site storefront (Russian-language catalogue)."
    ),
    requires_api_key=True,
    currency="KZT",
    # Kazakhstan is not present in roaster_location_codes.csv; Asia is the
    # closest supported location (the store is based in Almaty, Kazakhstan).
    country="Kazakhstan",
    status="experimental",
)
class MassimoCoffeeScraper(BaseScraper):
    """Scraper for Massimo Coffee (icoffee.store) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize the Massimo Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Massimo Coffee",
            base_url="https://icoffee.store",
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
        """Get store URLs to scrape.

        Returns:
            List containing the Ecwid all-products page.
        """
        return ["https://icoffee.store/products/"]

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page, narrowing product detail pages to the Ecwid product container.

        Ecwid Instant Site product pages embed all product content inside
        ``div.static-product-browser``. Narrowing to it strips the ~38 KB of
        theme boilerplate, i18n message blobs and scripts that surround the
        product before the HTML reaches the AI extractor.

        Args:
            *args: Positional arguments forwarded to the base fetch_page.
            **kwargs: Keyword arguments forwarded to the base fetch_page.

        Returns:
            BeautifulSoup object (narrowed for product pages) or None if the fetch failed.
        """
        soup = await super().fetch_page(*args, **kwargs)
        url = kwargs.get("url") or (args[0] if args else "")
        if soup is None:
            return None

        # `/products` and `/products/` are the listing page; only detail URLs
        # (`/products/<slug>`) get narrowed.
        if not url or "/products/" not in url:
            return soup
        if url.rstrip("/").endswith("/products"):
            return soup

        container = soup.select("div.static-product-browser")
        if len(container) == 1:
            logger.debug(f"Narrowed soup to div.static-product-browser for {url}")
            return container[0]
        logger.warning(f"Expected 1 div.static-product-browser for {url}, found {len(container)}")
        return soup

    # Sold-out detection: Ecwid card text detection ("Нет в наличии" = out of
    # stock). The check runs on the individual `.grid-product` card element —
    # never on the whole page, where the same string lives inside the Ecwid
    # i18n message blob ("OutOfStock.label":"Нет в наличии") and would
    # false-positive every product.
    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract in-stock coffee product URLs from the Ecwid category page.

        Args:
            store_url: URL of the all-products page.

        Returns:
            List of in-stock product URLs.
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        product_urls: list[str] = []
        seen: set[str] = set()

        for card in soup.select(".grid-product"):
            link = card.select_one("a[href*='/products/']")
            if not link:
                continue
            href = link.get("href")
            if not href or not isinstance(href, str):
                continue

            full_url = self.resolve_url(href.split("?")[0].split("#")[0])

            # Skip sold-out products before URL-pattern filtering.
            card_text = card.get_text(" ", strip=True)
            if "Нет в наличии" in card_text or "нет в наличии" in card_text.lower():
                logger.debug(f"Skipping sold-out product: {full_url}")
                continue

            slug = full_url.rstrip("/").rsplit("/", 1)[-1].lower()
            if slug in _CATEGORY_SLUGS:
                logger.debug(f"Skipping category page: {full_url}")
                continue
            if any(token in full_url.lower() for token in _EXTRA_EXCLUDED_SLUGS):
                logger.debug(f"Skipping equipment/merch URL: {full_url}")
                continue

            if not self.is_coffee_product_url(full_url, required_path_patterns=["/products/"]):
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
            # Russian-language catalogue.
            translate_to_english=True,
        )

    def postprocess_review_flags(self, bean: CoffeeBean, url: str) -> CoffeeBean:
        """Flag the Fermentation Project tasting set for review."""
        haystack = f"{url} {getattr(bean, 'name', '') or ''}".lower()
        if "fermentation-project" in haystack:
            bean.is_tasting_kit = True
        return bean

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Pin the store currency (the registry lookup by display name can fall back to GBP)."""
        bean.currency = "KZT"
        return bean
