"""Asylum Coffee scraper implementation with AI-powered extraction (Wix storefront).

Asylum Coffee | Swindon Specialty Roastery sells at www.asylumcoffee.co.uk, a
Wix storefront (parastorage.com assets, ``data-hook`` attributes, GBP prices).
The coffee catalogue lives under ``/category/`` (single-origins, house-blends,
mad-series, all-products), while brewing-equipments and merchs are non-coffee
categories and are excluded by category selection.
"""

import logging

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="asylum",
    display_name="Asylum Coffee",
    roaster_name="Asylum Coffee",
    website="https://www.asylumcoffee.co.uk",
    description="Asylum Coffee | Swindon Specialty Roastery - specialty coffee roasted "
    "in Swindon, United Kingdom, sold through the asylumcoffee.co.uk Wix store (GBP).",
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
            base_url="https://www.asylumcoffee.co.uk",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            The four coffee category URLs. Brewing-equipments and merchs are
            non-coffee and excluded. ``single-origins`` and ``all-products``
            paginate via ``?page=2`` (verified products render server-side);
            the other categories have a single page.
        """
        base = "https://www.asylumcoffee.co.uk/category"
        return [
            f"{base}/single-origins",
            f"{base}/single-origins?page=2",
            f"{base}/house-blends",
            f"{base}/mad-series",
            f"{base}/all-products",
            f"{base}/all-products?page=2",
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
            use_playwright=False,  # Wix renders product pages server-side (verified)
            use_optimized_mode=False,
            translate_to_english=False,
        )

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page and narrow product detail pages to the product content.

        This site's product pages do NOT provide ``div[data-hook="product-page"]``
        (a custom Wix template). The stable container is the page's single
        ``<main>`` element (id ``PAGE_SECTIONSnbms6`` on every product page),
        which holds the breadcrumb, title, price, gallery, description, and
        add-to-cart markup. Narrowing the soup to ``<main>`` typically drops a
        2+ MB page to ~100 KB of relevant markup before it reaches the AI
        extractor, a major token saving with zero information loss.

        Args:
            *args: Positional arguments forwarded to the base fetch_page.
            **kwargs: Keyword arguments forwarded to the base fetch_page.

        Returns:
            BeautifulSoup object (narrowed for product pages) or None if fetch failed.
        """
        try:
            soup = await super().fetch_page(*args, **kwargs)
            url = kwargs.get("url")
            if not url and len(args) > 0:
                url = args[0]
            # Only narrow product detail pages, leave listing/category pages untouched
            if "/product-page/" not in (url or ""):
                return soup
            if soup is None:
                return None
            main_el = soup.select("main")
            if len(main_el) == 1:
                logger.debug(f"Narrowed soup to <main> for {url}")
                return main_el[0]
            logger.warning(f"Expected 1 <main> for {url}, found {len(main_el)}")
            return soup
        except Exception as e:
            current_url = kwargs.get("url") or (args[0] if args else "?")
            logger.error(f"Error fetching page {current_url}: {e}")
            return None

    # Sold-out detection: Wix text detection on product-item-root container.
    # When a Wix product is sold out, the product card shows "Unavailable" /
    # "Sold out" / "Out of stock" text inside the product-item-root container.
    # We skip any product-item-root whose text contains those markers before
    # applying is_coffee_product_url filtering, so excluded products don't leak
    # past the stock check.
    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from the Wix store listing, filtering sold-out items.

        Args:
            store_url: URL of the category page (all coffee categories render HTML server-side)

        Returns:
            List of in-stock product URLs
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        product_urls: list[str] = []
        seen: set[str] = set()

        for item in soup.select('[data-hook="product-item-root"]'):
            link = item.select_one('a[href*="/product-page/"]')
            if not link:
                continue
            href = link.get("href")
            if not href or not isinstance(href, str):
                continue

            # Strip query string and fragment; resolve to absolute URL
            full_url = self.resolve_url(href.split("?")[0].split("#")[0])

            # Skip sold-out products before URL-pattern filtering
            item_text = item.get_text(" ", strip=True)
            if any(marker in item_text for marker in ("Unavailable", "Sold out", "Out of stock", "SOLD OUT")):
                logger.debug(f"Skipping sold-out product: {full_url}")
                continue

            # Apply standard coffee-product URL filtering (uses /product-page/ path pattern)
            if not self.is_coffee_product_url(full_url, required_path_patterns=["/product-page/"]):
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
