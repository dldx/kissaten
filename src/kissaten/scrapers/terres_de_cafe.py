"""Terres De Café coffee roastery scraper implementation with AI-powered extraction.

Terres De Café is a French specialty coffee roaster based in Paris. The store
runs on PrestaShop (not Shopify - there is no products.json endpoint).

The category listing no longer renders ``<article class="product-miniature">
tiles in raw HTML; instead each paginated listing page embeds a
``var stape_products = [...]`` JSON blob (a PrestaShop "stape" data-layer
featuring one entry per product with a fully-qualified ``link`` URL). We parse
that blob and follow the server-rendered ``?page=N`` pagination to walk the
whole collection.

Product detail pages embed a rich server-rendered ``data-product`` JSON plus a
human-readable data sheet (origin, variety, altitude, process, roaster, score),
all of which lives inside the ``.product__view`` container. ``fetch_page`` is
overridden to return only that container for product detail URLs, which keeps
AI token usage low without losing any coffee information.
"""

import json
import logging
import re

from bs4 import BeautifulSoup

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)

# Regex that grabs the ``var stape_products = [...]`` payload from the raw
# listing page HTML. The array is the single canonical product source on the
# current PrestaShop theme; ``article.product-miniature`` tiles no longer
# exist in the markup.
_STAPE_PRODUCTS_RE = re.compile(r"var\s+stape_products\s*=\s*(\[.*?\])\s*;", re.DOTALL)


@register_scraper(
    name="terres-de-cafe",
    display_name="Terres De Café",
    roaster_name="Terres De Café",
    website="https://www.terresdecafe.com",
    description="French specialty coffee roaster based in Paris, "
    "known for premium single-origin coffees and their high-end retail bags",
    requires_api_key=True,
    currency="EUR",
    country="France",
    status="available",
)
class TerresDeCafeScraper(BaseScraper):
    """Scraper for Terres De Café (terresdecafe.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Terres De Café scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Terres De Café",
            base_url="https://www.terresdecafe.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the specialty coffees collection URL.
        """
        # The "Speciality coffees" collection holds all 95 coffee products and
        # renders its full product listing in the raw HTML of page 1.
        return ["https://www.terresdecafe.com/en/13-speciality-coffees"]

    async def fetch_page(self, url: str, retries: int = 0, use_playwright: bool = False) -> BeautifulSoup | None:
        """Fetch a page, narrowing product detail pages to the info container.

        PrestaShop product pages carry all the coffee fields in a
        server-rendered ``.product__view`` container (name, price, the
        ``data-product`` JSON, and the human-readable data sheet). Returning
        only that container for product detail URLs keeps AI token usage low.
        Category/listing pages are returned untouched.

        Args:
            url: URL to fetch
            retries: Number of retries attempted
            use_playwright: Whether to use Playwright instead of httpx

        Returns:
            BeautifulSoup of the page, or the narrowed product container.
        """
        soup = await super().fetch_page(url, retries, use_playwright)
        if not soup:
            return None

        # Only narrow actual product detail pages (they end in .html and live
        # under the coffee product categories). Leave listing/category pages
        # intact.
        url_lower = url.lower()
        product_categories = (
            "/speciality-coffees/",
            "/gamme-legendes/",
            "/beans-coffee/",
        )
        if ".html" in url_lower and any(cat in url_lower for cat in product_categories):
            container = soup.select(".product__view")
            if len(container) == 1:
                return container[0]

        return soup

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
            translate_to_english=False,
        )

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from the specialty coffees listing pages.

        The current PrestaShop theme embeds a ``var stape_products = [...]``
        JSON blob on every paginated listing page; each entry carries a fully
        qualified ``link`` URL. We walk the server-rendered pagination
        (``?page=N``) and collect all coffee product URLs from every page.

        Args:
            store_url: URL of the first listing page

        Returns:
            List of product URLs
        """
        product_urls: list[str] = []
        seen: set[str] = set()

        page_url: str | None = store_url
        pages_visited = 0
        while page_url and pages_visited < 50:
            soup = await self.fetch_page(page_url)
            if soup is None:
                logger.warning(f"Listing fetch failed for {page_url}")
                break

            page_urls = self._parse_stape_products(str(soup))
            if not page_urls:
                logger.warning(f"No stape_products parsed from {page_url}")
                break

            for url in page_urls:
                if url not in seen:
                    seen.add(url)
                    product_urls.append(url)

            pages_visited += 1
            page_url = self._next_listing_page(str(soup), page_url)

        logger.info(f"Found {len(product_urls)} coffee product URLs across {pages_visited} pages from {store_url}")
        return product_urls

    def _parse_stape_products(self, html: str) -> list[str]:
        """Parse the ``var stape_products = [...]`` JSON blob from listing HTML.

        Args:
            html: Raw HTML of a listing page (BeautifulSoup str() form works).

        Returns:
            List of product URLs found on this page.
        """
        match = _STAPE_PRODUCTS_RE.search(html)
        if not match:
            return []

        try:
            entries = json.loads(match.group(1))
        except json.JSONDecodeError as exc:
            logger.warning(f"Could not parse stape_products JSON: {exc}")
            return []

        urls: list[str] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            link = entry.get("link")
            if not link or not isinstance(link, str):
                continue

            canonical = self.resolve_url(link.split("#")[0])
            # The specialty-coffees listing cross-lists the premium Légendes
            # (/en/gamme-legendes/) and Beans Coffee (/en/beans-coffee/)
            # products; keep those and let is_coffee_product_url reject the
            # non-bean categories (capsules, machines, accessories, etc.).
            if self.is_coffee_product_url(
                canonical,
                required_path_patterns=["/speciality-coffees/", "/gamme-legendes/", "/beans-coffee/"],
            ):
                urls.append(canonical)
        return urls

    def _next_listing_page(self, html: str, current_url: str) -> str | None:
        """Find the next paginated listing URL, if any.

        The PrestaShop theme renders pagination as anchor tags with
        ``data-page-link`` pointing at ``<store_url>?page=N``.

        Args:
            html: Raw HTML of the current listing page.
            current_url: URL of the current listing page.

        Returns:
            The next page URL, or None when on the last page.
        """
        soup = BeautifulSoup(html, "html.parser")
        current_page = 1
        if "?page=" in current_url:
            try:
                current_page = int(current_url.split("?page=")[1].split("&")[0])
            except (ValueError, IndexError):
                current_page = 1

        for link in soup.select("a[data-page-link]"):
            href = link.get("href")
            if not href:
                continue
            if "?page=" not in href:
                continue
            try:
                page_no = int(href.split("?page=")[1].split("&")[0])
            except (ValueError, IndexError):
                continue
            if page_no == current_page + 1:
                return self.resolve_url(href)
        return None
