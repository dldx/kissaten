"""Humpback Whale Coffee scraper with AI extraction.

The new humpbackwhalecoffee.com site is a Next.js App Router app. Every
product page embeds all of the bean's metadata inside a single
``<script>self.__next_f.push([1, "..."])</script>`` block as a JSON
string. We pull that whole script tag out of the page and hand it to the
AI extractor instead of the raw HTML, which is far easier for the model
to parse.
"""

import logging

from bs4 import BeautifulSoup

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="humpback-whale",
    display_name="Humpback Whale Coffee",
    roaster_name="Humpback Whale Coffee",
    website="https://humpbackwhalecoffee.com",
    description="Specialty coffee roaster based in Munich, Germany.",
    requires_api_key=True,
    currency="EUR",
    country="Germany",
    status="available",
)
class HumpbackWhaleCoffeeScraper(BaseScraper):
    """Scraper for humpbackwhalecoffee.com — feeds the product's Next.js
    Flight ``<script>`` block to the AI extractor."""

    def __init__(self, api_key: str | None = None):
        super().__init__(
            roaster_name="Humpback Whale Coffee",
            base_url="https://humpbackwhalecoffee.com",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        return ["https://humpbackwhalecoffee.com/shop"]

    async def fetch_page(
        self, url: str, retries: int = 0, use_playwright: bool = False
    ) -> BeautifulSoup | None:
        """Replace product-page HTML with the raw Next.js Flight script tag.

        For any URL under ``/shop/<slug>`` we find the
        ``<script>self.__next_f.push([1, "..."])</script>`` block whose
        payload contains the slug, then return a minimal soup whose
        ``str()`` is just that script tag. The AI extractor in
        ``BaseScraper._extract_bean_with_ai`` reads ``str(soup)`` directly,
        so it ends up consuming the structured JSON inside the script.
        """
        soup = await super().fetch_page(url, retries, use_playwright)
        if soup is None:
            return None

        # Only massage product pages; the shop listing is plain HTML.
        slug = self._product_slug(url)
        if slug is None:
            return soup

        target = self._find_product_script(soup, slug)
        if target is None:
            logger.warning("No Next.js product script tag found for slug %r", slug)
            return soup

        return BeautifulSoup(str(target), "lxml")

    @staticmethod
    def _product_slug(url: str) -> str | None:
        parts = [p for p in url.rstrip("/").split("/") if p]
        if len(parts) < 2 or parts[-2] != "shop":
            return None
        return parts[-1] or None

    @staticmethod
    def _find_product_script(soup: BeautifulSoup, slug: str) -> object | None:
        """Return the ``<script>self.__next_f.push(...)`` block that carries
        this product's data.

        The page embeds several ``__next_f.push`` payloads (routing info,
        the main product, related products, the "you may also like" block).
        The main product's payload is the only one that contains both the
        escaped ``\"slug\":\"<slug>\"`` field and a ``\"coffee\":`` object,
        so we look for that intersection.
        """
        slug_marker = f'\\"slug\\":\\"{slug}\\"'
        coffee_marker = '\\"coffee\\":'
        for script in soup.find_all("script"):
            text = script.string or script.get_text()
            if "self.__next_f.push" not in text:
                continue
            if slug_marker in text and coffee_marker in text:
                return script
        return None

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        if not product_urls:
            return []

        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=False,
        )

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Pull every product slug from the /shop landing page."""
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        urls: set[str] = set()
        for anchor in soup.find_all("a", href=True):
            href = anchor.get("href")
            if not isinstance(href, str):
                continue
            path = href.split("?", 1)[0].rstrip("/")
            if not path.startswith("/shop/"):
                continue
            slug = path[len("/shop/"):]
            if not slug or "/" in slug:
                continue
            urls.add(self.resolve_url(path))
        return sorted(urls)

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        bean.currency = "EUR"
        return bean
