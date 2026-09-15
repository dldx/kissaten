"""Critical Beans scraper implementation with AI-powered extraction.

Critical Beans (criticalbeansit.be) is a Belgian fair-coffee roastery and
IT/AI consultancy. The storefront is a React single-page app (no server-rendered
HTML at all — ``<div id="root">`` is empty), so there are no product pages to
scrape. Instead the app is backed by a public JSON API:

- ``GET /api/products``       — full product listing (name, slug, category,
                                description, price, sizes, stock, image)
- ``GET /api/products/<slug>``— single product detail

We use the JSON API for both discovery and extraction: the listing supplies
in-stock coffee product URLs (``/shop/<slug>`` routes, used as stable bean
identity), and ``fetch_page`` converts the per-product JSON into a small
synthetic HTML document that feeds the standard AI extraction flow.
"""

import json
import logging

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)

API_PRODUCTS_URL = "https://criticalbeansit.be/api/products"


@register_scraper(
    name="critical-beans",
    display_name="Critical Beans",
    roaster_name="Critical Beans",
    website="https://criticalbeansit.be",
    description=(
        "Belgian fair-coffee roastery and IT/AI consultancy (Critical Beans IT) "
        "selling single-origin coffee and tasting sets from a React storefront "
        "with a JSON API backend."
    ),
    requires_api_key=True,
    currency="EUR",
    country="Belgium",
    status="experimental",
)
class CriticalBeansScraper(BaseScraper):
    """Scraper for Critical Beans (criticalbeansit.be JSON API)."""

    def __init__(self, api_key: str | None = None):
        """Initialize Critical Beans scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Critical Beans",
            base_url="https://criticalbeansit.be",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get the JSON API product listing endpoint."""
        return [API_PRODUCTS_URL]

    @staticmethod
    def _parse_products_json(soup: BeautifulSoup | Tag | None) -> list[dict] | None:
        """Parse a Store API JSON document out of a fetched soup.

        Args:
            soup: BeautifulSoup of the fetched API response

        Returns:
            List of product dicts, or None if the response was not valid JSON.
        """
        if soup is None:
            return None
        try:
            data = json.loads(soup.get_text())
        except (json.JSONDecodeError, ValueError):
            logger.warning("Could not parse Critical Beans API response as JSON")
            return None
        if not isinstance(data, list | dict):
            logger.warning("Unexpected Critical Beans API response shape")
            return None
        return data

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
            translate_to_english=False,  # storefront copy is already English
        )

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch product "pages" via the JSON API and synthesize an HTML document.

        The React storefront has no server-rendered product pages, so for
        ``/shop/<slug>`` URLs we fetch ``/api/products/<slug>`` and render a
        minimal HTML document (name, description, price, sizes, stock, image)
        for the AI extractor. API listing URLs are returned as-is.

        Args:
            *args: Positional arguments forwarded to the base fetch_page.
            **kwargs: Keyword arguments forwarded to the base fetch_page.

        Returns:
            BeautifulSoup object (synthetic product page) or None if fetch failed.
        """
        try:
            soup = await super().fetch_page(*args, **kwargs)
            url = kwargs.get("url")
            if not url and len(args) > 0:
                url = args[0]
            if "/shop/" not in (url or ""):
                if soup is None:
                    return None
                return soup

            slug = url.rstrip("/").split("/shop/")[-1].split("?")[0]
            if not slug:
                logger.warning(f"Could not determine product slug from {url}")
                return None
            detail_soup = await super().fetch_page(f"{API_PRODUCTS_URL}/{slug}")
            data = self._parse_products_json(detail_soup)
            if not isinstance(data, dict):
                logger.warning(f"No JSON product detail for {url}")
                return None
            return self._render_product_html(data)
        except Exception as e:
            logger.error(f"Error fetching page {url if 'url' in dir() else '?'}: {e}")
            return None

    @staticmethod
    def _render_product_html(product: dict) -> BeautifulSoup:
        """Render an API product dict as a minimal HTML document for AI extraction.

        Args:
            product: Product dict from the Critical Beans API

        Returns:
            BeautifulSoup of a small synthetic product page
        """
        price = product.get("price")
        sizes = ", ".join(str(s) for s in product.get("sizes") or []) or "n/a"
        stock = product.get("stock")
        availability = "In stock" if (stock is None or stock > 0) else "Out of stock"

        image = product.get("image")
        img_tag = f'<img src="{image}" alt="{product.get("name", "")}"/>' if image else ""

        html = (
            "<html><head><title>Critical Beans product</title></head><body>"
            f"<h1>{product.get('name', '')}</h1>"
            f"<p>{product.get('description', '')}</p>"
            f"<p>Price: {price} EUR</p>"
            f"<p>Size: {sizes}</p>"
            f"<p>Availability: {availability}</p>"
            f"{img_tag}"
            "</body></html>"
        )
        return BeautifulSoup(html, "html.parser")

    # Sold-out detection: JSON API `stock` field. The React storefront has no
    # HTML cards to inspect; the API listing exposes per-product stock counts
    # directly. Products with stock == 0 are skipped before
    # is_coffee_product_url filtering, so excluded products don't leak past
    # the stock check.
    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract in-stock coffee product URLs from the JSON API listing.

        Args:
            store_url: The /api/products listing URL

        Returns:
            List of in-stock coffee product URLs (``/shop/<slug>`` routes)
        """
        soup = await self.fetch_page(store_url)
        data = self._parse_products_json(soup)
        if data is None:
            # Listing fetch failed — return [] so the base class records the
            # failed listing and skips out-of-stock diffjson updates.
            return []

        products = data if isinstance(data, list) else []
        product_urls: list[str] = []
        for product in products:
            if product.get("category") != "coffee":
                continue  # skip merch (t-shirts etc.)
            slug = product.get("slug")
            if not slug or not isinstance(slug, str):
                continue
            # Sold-out detection: stock == 0 means sold out / pre-order closed
            if product.get("stock") == 0:
                logger.debug(f"Skipping sold-out product: {slug}")
                continue
            product_urls.append(f"{self.base_url}/shop/{slug}")

        coffee_urls = [
            url for url in product_urls if self.is_coffee_product_url(url, required_path_patterns=["/shop/"])
        ]
        logger.info(f"Found {len(coffee_urls)} in-stock coffee product URLs from {store_url}")
        return coffee_urls

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Force the currency to EUR.

        The API reports prices as plain numbers without a currency field, so
        the base class currency detection never fires and default_currency
        falls back to GBP. Critical Beans sells in euros.

        Args:
            bean: Extracted CoffeeBean object

        Returns:
            The bean with currency forced to EUR
        """
        bean.currency = "EUR"
        for option in bean.price_options or []:
            option.currency = "EUR"
        return bean
