"""Fathers coffee roastery scraper implementation with AI-powered extraction.

Fathers (fathers.cz) is a Czech specialty coffee roastery based in Ostrava.
The site is a custom SvelteKit storefront (not Shopify). The English view
lives under `/en` and product categories are nested under `/en/coffee/`:

- `/en/coffee/filter`   -> filter-roast whole beans
- `/en/coffee/espresso` -> espresso-roast whole beans
- `/en/coffee/dripbags` / `/en/coffee/capsules` / `/en/coffee/courses` (not coffee beans)

We only collect the filter and espresso categories. Product detail pages are
server-rendered with full text plus schema.org ProductGroup JSON-LD, so plain
httpx (no Playwright) is sufficient.
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


@register_scraper(
    name="fathers",
    display_name="Fathers",
    roaster_name="Fathers",
    website="https://fathers.cz",
    description="Czech specialty coffee roastery based in Ostrava, roasting "
    "single-origin filter and espresso coffees",
    requires_api_key=True,
    currency="CZK",
    country="Czechia",
    status="available",
)
class FathersScraper(BaseScraper):
    """Scraper for Fathers (fathers.cz) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Fathers scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Fathers",
            base_url="https://fathers.cz",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List of coffee category URLs (filter + espresso beans only)
        """
        return [
            "https://fathers.cz/en/coffee/filter",
            "https://fathers.cz/en/coffee/espresso",
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
            use_playwright=False,
            use_optimized_mode=False,
            translate_to_english=False,  # English product pages are already in English
        )

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from a store (category) page.

        Args:
            store_url: URL of the store page

        Returns:
            List of coffee bean product URLs
        """
        # Sold-out detection: the Fathers listings do not expose any sold-out
        # marker on the product cards (no sold-out/out-of-stock class or text),
        # so there is nothing to filter at the link level. Products that sell
        # out are resolved by the AI extractor from the product detail page
        # (schema.org availability / "In stock"/"Out of stock" text).
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        # Collect only whole-bean coffee products (filter/espresso categories).
        product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/en/coffee/filter/", "/en/coffee/espresso/"],
            selectors=[
                'article.product-card a[href*="/en/coffee/"]',
                'a[href*="/en/coffee/filter/"]',
                'a[href*="/en/coffee/espresso/"]',
            ],
        )

        logger.info(f"Found {len(product_urls)} coffee product URLs from {store_url}")
        return product_urls

    async def fetch_page(self, url: str, retries: int = 0, use_playwright: bool = False) -> BeautifulSoup | None:
        """Fetch a page, narrowing product detail pages to a clean single-currency snippet.

        The Fathers storefront embeds a large (500KB+) JSON blob on every product page
        carrying prices in many currencies per country tax rate, and the rendered page
        displays prices in EUR on the English view. That multi-currency noise makes the
        AI extractor emit inconsistent prices. To keep data quality, we reduce every
        product detail page to a small English snippet with the roaster's home currency
        price (CZK) resolved from the embedded JSON, so the AI sees one unambiguous price.

        Args:
            url: URL to fetch
            retries: Number of retries attempted
            use_playwright: Whether to use Playwright instead of httpx

        Returns:
            BeautifulSoup object or None if failed
        """
        soup = await super().fetch_page(url, retries, use_playwright)
        if not soup:
            return None

        # Only narrow whole-bean product detail pages; leave category/listing pages alone.
        if not (("/en/coffee/filter/" in url) or ("/en/coffee/espresso/" in url)):
            return soup

        snippet = self._render_product_snippet(soup, url)
        return BeautifulSoup(snippet, "html.parser") if snippet else soup

    async def _extract_bean_with_ai(
        self,
        ai_extractor,
        soup: BeautifulSoup,
        product_url: str,
        use_optimized_mode: bool = False,
        translate_to_english: bool = False,
    ) -> CoffeeBean | None:
        """Extract a bean with AI, then pin the authoritative CZK price/currency.

        The Gemini extractor is unreliable at assigning the currency on this
        multi-currency storefront (it often falls back to GBP). Since the CZK
        price is resolved deterministically from the embedded product JSON (and
        rendered into the snippet by ``_render_product_snippet``), we override
        ``currency`` and ``price`` on the returned bean so the stored data is
        consistent and correct. AI extraction is still used for the descriptive
        fields (origin, variety, processing, tasting notes, name).

        Args:
            ai_extractor: AI extractor instance
            soup: BeautifulSoup of the (narrowed) product page
            product_url: URL of the product page
            use_optimized_mode: Whether to use optimized mode
            translate_to_english: Whether to translate results to English

        Returns:
            CoffeeBean with CZK price pinned, or None if extraction failed
        """
        bean = await super()._extract_bean_with_ai(
            ai_extractor, soup, product_url, use_optimized_mode, translate_to_english
        )
        if bean is None:
            return None

        czk_price = self._price_from_snippet(soup)
        if czk_price is not None:
            bean.currency = "CZK"
            bean.price = czk_price
        return bean

    @staticmethod
    def _price_from_snippet(soup: BeautifulSoup) -> float | None:
        """Read the CZK price back out of a rendered product snippet.

        Args:
            soup: BeautifulSoup of the narrowed product snippet

        Returns:
            The CZK price or None if not present
        """
        text = soup.get_text(" ", strip=True)
        match = re.search(r"Price:\s*([\d.]+)\s*CZK", text)
        return float(match.group(1)) if match else None

    def _render_product_snippet(self, soup: BeautifulSoup, product_url: str) -> str | None:
        """Build a concise English + CZK HTML snippet for a product detail page.

        Args:
            soup: BeautifulSoup of the full product page
            product_url: The product URL

        Returns:
            A minimal HTML string with name, description and a single CZK price,
            or None if the embedded product JSON could not be parsed.
        """
        data = self._parse_embedded_product(soup)
        if not data:
            logger.debug(f"No embedded product JSON found for {product_url}")
            return None

        product = data.get("product", {})
        name = (product.get("name") or {}).get("en") or (product.get("name") or {}).get("cs") or product_url
        short = (product.get("shortDescription") or {}).get("en", "")
        description = (product.get("description") or {}).get("en", "")

        price_czk = self._primary_czk_price(product)

        parts = ["<html><body>", f"<h1>{name}</h1>", f"<p>Product URL: {product_url}</p>"]
        if price_czk is not None:
            parts.append(f"<p>Price: {price_czk:.2f} CZK</p>")
        if short:
            parts.append(f"<p>{short}</p>")
        if description:
            parts.append(f"<div>{description}</div>")
        parts.append("</body></html>")
        return "".join(parts)

    @staticmethod
    def _parse_embedded_product(soup: BeautifulSoup) -> dict | None:
        """Extract the embedded ``{"product": {...}}`` JSON blob from a product page.

        Args:
            soup: BeautifulSoup of the full product page

        Returns:
            Parsed JSON dict or None if not found
        """
        for script in soup.find_all("script"):
            text = (script.string or "").strip()
            if not text.startswith('{"product"'):
                continue
            try:
                return json.loads(text)
            except (json.JSONDecodeError, ValueError):
                continue
        return None

    @staticmethod
    def _primary_czk_price(product: dict) -> float | None:
        """Return the Czech (CZK) retail price for the primary (smallest) variant.

        Args:
            product: The parsed product dict

        Returns:
            The CZK price with tax for the smallest weight variant, or None.
        """
        variants = product.get("variants") or []
        if not variants:
            return None
        primary = min(variants, key=lambda v: v.get("weightInGrams") or 0)
        czk = (primary.get("prices") or {}).get("CZK") or {}
        if not czk:
            return None

        # Prefer the tax-rate bucket that includes Czechia; fall back to rate "12".
        for rate, record in czk.items():
            if "Czechia" in (record.get("countries") or []):
                price = (record.get("price") or {}).get("withTax")
                if price is not None:
                    return float(price)
        record = czk.get("12")
        price = (record or {}).get("price")
        return float(price["withTax"]) if price and price.get("withTax") is not None else None
