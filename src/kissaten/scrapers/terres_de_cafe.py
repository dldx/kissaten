"""Terres De Café coffee roastery scraper implementation with AI-powered extraction.

Terres De Café is a French specialty coffee roaster based in Paris. The store
runs on PrestaShop (not Shopify - there is no products.json endpoint). Product
listings are server-rendered bare HTML, so the koppi scraping model applies:
fetch the category page, collect product URLs from the raw markup, and run AI
extraction on each product detail page.

Product detail pages embed a rich server-rendered ``data-product`` JSON plus a
human-readable data sheet (origin, variety, altitude, process, roaster, score),
all of which lives inside the ``.product__view`` container. ``fetch_page`` is
overridden to return only that container for product detail URLs, which keeps
AI token usage low without losing any coffee information.
"""

import logging

from bs4 import BeautifulSoup

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


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

    async def fetch_page(
        self, url: str, retries: int = 0, use_playwright: bool = False
    ) -> BeautifulSoup | None:
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
        """Extract product URLs from the specialty coffees listing page.

        Args:
            store_url: URL of the store page

        Returns:
            List of product URLs
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        product_urls = []
        # Each product is an <article class="product-miniature"> with a link to
        # /en/speciality-coffees/<id>-<slug>.html (optionally followed by a
        # "#/..." variant fragment that we drop to get the canonical URL). The
        # speciality-coffees listing also cross-lists the premium Légendes
        # coffees (/en/gamme-legendes/) and a few /en/beans-coffee/ products,
        # so we accept any tile product link and let is_coffee_product_url
        # reject the non-bean categories (capsules, batch-discovery, etc.).
        for product in soup.select("article.product-miniature"):
            link = product.select_one('a[href$=".html"], a[href*=".html#"]')
            if link is None or not link.get("href"):
                continue

            href = link["href"]
            # Sold-out detection: text detection on the product card. Apply
            # before is_coffee_product_url so oos products don't leak through.
            card_text = product.get_text(" ", strip=True).lower()
            if any(
                marker in card_text
                for marker in ("sold out", "out of stock", "épuisé", "rupture", "indisponible")
            ):
                continue

            # Drop the PrestaShop variant fragment to get the canonical URL.
            canonical = self.resolve_url(href.split("#")[0])
            if self.is_coffee_product_url(
                canonical,
                required_path_patterns=["/speciality-coffees/", "/gamme-legendes/", "/beans-coffee/"],
            ):
                product_urls.append(canonical)

        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in product_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        logger.info(f"Found {len(unique_urls)} coffee product URLs from {store_url}")
        return unique_urls
