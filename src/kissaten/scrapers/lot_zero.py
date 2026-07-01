"""Lot Zero coffee roaster scraper implementation with AI-powered extraction."""

import logging

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="lot-zero",
    display_name="Lot Zero",
    roaster_name="Lot Zero",
    website="https://www.7gr.it",
    description="Italian specialty coffee micro-roastery by Chiara Bergonzi, part of 7Gr., "
    "offering single-origin and experimental lots under the Lot Zero label.",
    requires_api_key=True,
    currency="EUR",
    country="Italy",
    status="available",
)
class LotZeroScraper(BaseScraper):
    """Scraper for Lot Zero (7gr.it) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Lot Zero scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Lot Zero",
            base_url="https://www.7gr.it",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        The Lot Zero catalogue is paginated via WordPress /page/N/ paths.

        Returns:
            List of Lot Zero collection page URLs.
        """
        return [
            "https://www.7gr.it/en/product-category/coffee/specialty-coffee-lot-zero-en/",
            "https://www.7gr.it/en/product-category/coffee/specialty-coffee-lot-zero-en/page/2/",
        ]

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page and return a reduced soup for AI extraction.

        For product pages, limit the soup to the first two
        ``div.elementor-element`` children inside the
        ``div[data-elementor-type="product"]`` wrapper. Those two elements
        contain the breadcrumb, title, description and image - everything
        the AI extractor needs - while dropping the rest of the page
        (header, footer, related products, etc.) to reduce token count.

        Args:
            *args: Positional args forwarded to ``super().fetch_page``.
            **kwargs: Keyword args forwarded to ``super().fetch_page``.

        Returns:
            Reduced BeautifulSoup/Tag, or None if the fetch failed.
        """
        try:
            soup = await super().fetch_page(*args, **kwargs)
            url = kwargs.get("url")
            if not url and len(args) > 0:
                url = args[0]

            if not isinstance(soup, (BeautifulSoup, Tag)) or "/en/product/" not in (url or ""):
                return soup

            product_section = soup.select_one('div[data-elementor-type="product"]')
            if not product_section:
                return soup

            elementor_divs = product_section.select("div.elementor-element")
            if len(elementor_divs) < 2:
                return soup

            trimmed = BeautifulSoup("", "lxml")
            for el in elementor_divs[:2]:
                trimmed.append(el)

            logger.debug(f"Trimmed product page to first 2 elementor divs: {url}")
            return trimmed
        except Exception as e:
            logger.error(f"Error fetching page {kwargs.get('url') or (args[0] if args else '?')}: {e}")
            return None

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

    def _get_excluded_url_patterns(self) -> list[str]:
        """Exclude non-bean products (brew bags, etc.) from the Lot Zero catalogue.

        Returns:
            List of URL patterns to exclude.
        """
        return super()._get_excluded_url_patterns() + [
            "brew-bag",  # Drip/brew bag coffee (not whole/ground beans)
            "brew_bag",
            "drip-bag",
            "drip_bag",
            "capsule",
            "pod",
        ]

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from a Lot Zero category page.

        Sold-out detection: WooCommerce class detection. The Elementor loop-item
        container exposes WooCommerce's stock status as a class
        (`outofstock` for sold-out, `instock` for available). We skip any
        container carrying the `outofstock` class before the standard
        coffee URL filter runs.

        Args:
            store_url: URL of the store page

        Returns:
            List of in-stock product URLs
        """
        soup = await self.fetch_page(store_url, use_playwright=False)
        if not soup:
            return []

        product_urls: list[str] = []
        # Sold-out detection: class (WooCommerce `outofstock` on Elementor loop item)
        for item in soup.select(".e-loop-item"):
            classes = item.get("class", []) or []
            if "outofstock" in classes:
                logger.debug(f"Skipping sold-out product on {store_url}: {[c for c in classes if 'stock' in c]}")
                continue

            link = item.select_one('a[href*="/en/product/"]')
            if not isinstance(link, Tag):
                continue
            href = link.get("href")
            if not href or not isinstance(href, str):
                continue

            full_url = self.resolve_url(href).split("?")[0]
            if self.is_coffee_product_url(full_url, required_path_patterns=["/en/product/"]):
                product_urls.append(full_url)

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_urls: list[str] = []
        for url in product_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        logger.info(f"Found {len(unique_urls)} in-stock product URLs from {store_url}")
        return unique_urls
