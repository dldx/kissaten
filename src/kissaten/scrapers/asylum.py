"""Asylum Coffee scraper implementation with AI-powered extraction (Atom Sites storefront).

Asylum Coffee | Swindon Specialty Roastery sells at asylumcoffee.co.uk. The
store migrated off Wix to a custom **Atom Sites** storefront (verified live
2026-11: every ``/category/*`` URL 301-redirects to the homepage ``/#shop``,
and the Wix ``parastorage``/``data-hook`` markup is gone).

The whole coffee catalogue is a single server-side rendered shop grid on the
homepage (``<div id="shop" data-shop-filter>``): product cards are
``article.card`` elements carrying ``data-product-id`` and a (usually
empty-string) ``data-available`` attribute, with ``/products/<slug>`` links.
Client-side category filters (house-blends / single-origins / decaf /
subscribable) are data-attribute toggles on the same grid — there are no
separate category pages, so a single store URL covers everything.

Product pages live at ``/products/<slug>`` and carry ``@type: Product`` JSON-LD
plus GBP prices.
"""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)

STORE_URL = "https://asylumcoffee.co.uk/"


@register_scraper(
    name="asylum",
    display_name="Asylum Coffee",
    roaster_name="Asylum Coffee",
    website="https://asylumcoffee.co.uk",
    description="Asylum Coffee | Swindon Specialty Roastery - specialty coffee roasted "
    "in Swindon, United Kingdom, sold through the asylumcoffee.co.uk Atom Sites store (GBP).",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class AsylumScraper(BaseScraper):
    """Scraper for Asylum Coffee (asylumcoffee.co.uk) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Asylum Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Asylum Coffee",
            base_url="https://asylumcoffee.co.uk",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            The homepage shop grid URL. The Atom Sites storefront renders the
            whole coffee catalogue server-side on the homepage
            (``/#shop`` section); the former Wix category pages
            (``/category/single-origins``, ``/category/house-blends``, ...) now
            301-redirect to it, and in-page filters are client-side toggles.
        """
        return [STORE_URL]

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
            use_playwright=False,  # Atom Sites renders product pages server-side (verified)
            use_optimized_mode=False,
            translate_to_english=False,
        )

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from the homepage shop grid, filtering sold-out items.

        Args:
            store_url: URL of the homepage (``/#shop`` section, server-rendered)

        Returns:
            List of in-stock product URLs
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        product_urls: list[str] = []
        seen: set[str] = set()

        # Product cards: <article class="card" data-product-id="..." data-available="...">
        for item in soup.select("article.card"):
            link = item.select_one('a[href*="/products/"]')
            if not link:
                continue
            href = link.get("href")
            if not href or not isinstance(href, str):
                continue

            # Strip query string and fragment; resolve to absolute URL
            full_url = self.resolve_url(href.split("?")[0].split("#")[0])

            # Skip sold-out products before URL-pattern filtering. Available
            # cards carry an empty-string ``data-available`` attribute; a
            # "false" value or sold-out badge text means unavailable.
            available_attr = item.get("data-available")
            if isinstance(available_attr, str) and available_attr.strip().lower() == "false":
                logger.debug(f"Skipping sold-out product (data-available=false): {full_url}")
                continue

            item_text = item.get_text(" ", strip=True)
            if any(marker in item_text for marker in ("Sold out", "Sold Out", "SOLD OUT", "Unavailable")):
                logger.debug(f"Skipping sold-out product (badge text): {full_url}")
                continue

            # Apply standard coffee-product URL filtering (uses /products/ path pattern)
            if not self.is_coffee_product_url(full_url, required_path_patterns=["/products/"]):
                continue

            if full_url not in seen:
                seen.add(full_url)
                product_urls.append(full_url)

        logger.info(f"Found {len(product_urls)} in-stock product URLs from {store_url}")
        return product_urls

    def postprocess_extracted_bean(self, bean):
        """Pin the bean currency to GBP (the site sells exclusively in GBP)."""
        bean = super().postprocess_extracted_bean(bean)
        bean.currency = "GBP"
        return bean
