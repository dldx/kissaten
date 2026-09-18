"""Mundos Roasting & Co. scraper implementation with AI extraction (Squarespace)."""

import html as html_module
import json
import logging
import re

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="mundos-roasting",
    display_name="Mundos Roasting",
    roaster_name="Mundos Roasting",
    website="https://www.mundosroastingco.com",
    description=(
        "Specialty coffee roaster and cafe group based in Traverse City, Michigan, "
        "sourcing and roasting single-origin coffees alongside chocolate and tea."
    ),
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class MundosRoastingScraper(BaseScraper):
    """Scraper for Mundos Roasting (mundosroastingco.com) — a Squarespace storefront.

    The ``/coffee`` collection page renders its product grid via JS, but the full
    catalog is embedded in the initial HTML as an escaped Squarespace JSON blob
    containing ``fullUrl``, ``urlSlug`` and per-product ``qtyInStock`` — which we
    use for discovery and sold-out filtering. Product detail pages carry the
    standard Squarespace ``og:*/product:*`` meta tags plus the
    ``Static.SQUARESPACE_CONTEXT`` variants JSON, so we follow the Pala
    meta-only narrowing pattern.
    """

    # Squarespace qtyInStock sentinel for "unlimited" stock.
    _UNLIMITED_STOCK = 9223372036854775807

    # Non-coffee URL slug substrings (chocolate, matcha, merch, bar gear).
    _excluded_url_slugs = [
        "chocolate",  # house chocolate bars / 3-packs
        "matcha",  # ceremonial matcha
        "beanie",  # merch
        "mug",  # drinkware
        "slow-bar",  # bar serving option, not bagged beans
        "test",  # internal test product
    ]

    def __init__(self, api_key: str | None = None):
        """Initialize Mundos Roasting scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Mundos Roasting",
            base_url="https://www.mundosroastingco.com",
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
        """Return the Squarespace coffee collection listing URL."""
        return ["https://www.mundosroastingco.com/coffee"]

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction + page screenshot."""
        if not product_urls:
            return []

        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=False,
            use_optimized_mode=True,  # Send a page screenshot for visual/roast info
            translate_to_english=False,  # Site is in English
        )

    async def fetch_page(self, *args, **kwargs):
        """Send the product-page meta tags plus the parsed size/price variants to
        the extractor — visual/roast info comes from the page screenshot."""
        soup = await super().fetch_page(*args, **kwargs)
        url = kwargs.get("url") or (args[0] if args else "")
        if "/coffee/p/" not in url:
            return soup

        # Mundos' structured data lives in <head> meta tags. The og:description
        # carries name/tasting/origin/process; product:* carries price, currency
        # and availability. The visual/roast info comes from the screenshot.
        compact = BeautifulSoup("<html><head></head><body></body></html>", "html.parser")
        keep_meta = {
            "og:title",
            "og:description",
            "og:url",
            "og:type",
            "product:price:amount",
            "product:price:currency",
            "product:availability",
        }
        for meta in soup.find_all("meta"):
            key = meta.get("property") or meta.get("itemprop") or meta.get("name")
            if key in keep_meta or meta.get("name") == "description":
                compact.head.append(meta)

        compact.body.append(self._extract_variants(soup))
        return compact

    @staticmethod
    def _extract_variants(soup: BeautifulSoup) -> Tag:
        """Parse the Squarespace static-context script for per-variant size/price.

        Squarespace embeds the product's variants (size, price, currency, stock)
        inside a <script data-name="static-context"> as the JSON blob
        "Static.SQUARESPACE_CONTEXT = {...}".
        """
        container = BeautifulSoup("<div></div>", "html.parser").div
        script = soup.find("script", {"data-name": "static-context"})
        if script is None:
            return container

        blob = script.string or script.get_text() or ""
        match = re.search(r"Static\.SQUARESPACE_CONTEXT\s*=\s*(\{.*?\})\s*;\s*$", blob, re.DOTALL)
        if not match:
            return container

        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError:
            return container

        product = data.get("product") or {}
        variants = product.get("variants") or []
        if not variants:
            return container

        lines = ["Variants:"]
        for v in variants:
            attrs = v.get("attributes") or {}
            size = "; ".join(str(val) for val in attrs.values()) or "n/a"
            price = (v.get("price") or {}).get("decimalValue")
            currency = (v.get("price") or {}).get("currencyCode")
            stock = "instock" if (v.get("stock") or {}).get("unlimited") else "unknown"
            lines.append(f"- Size: {size} | Price: {price} {currency} | Stock: {stock}")
        container.string = "\n".join(lines)
        return container

    # Sold-out detection: product-level qtyInStock == 0 in the escaped
    # Squarespace collection JSON embedded in the listing page. Products with
    # qtyInStock 0 are skipped during extraction, before any URL filtering, so
    # excluded (non-coffee) products can never leak past the stock check. The
    # unlimited-stock sentinel (2^63-1) counts as in stock.
    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract in-stock coffee product URLs from the Squarespace collection JSON.

        Args:
            store_url: URL of the /coffee collection page

        Returns:
            List of in-stock coffee product URLs
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        # The product catalog is embedded as HTML-escaped JSON (data attributes
        # / script payloads) with entries like:
        #   "fullUrl":"/coffee/p/colombia-argelia","urlSlug":"colombia-argelia","qtyInStock":471
        raw_html = html_module.unescape(str(soup))
        matches = re.findall(
            r'"fullUrl":"(/coffee/p/[a-z0-9-]+)","urlSlug":"[^"]*","qtyInStock":(\d+)',
            raw_html,
        )
        logger.info(f"Found {len(matches)} products in the Squarespace collection JSON")

        product_urls = []
        for path, qty in matches:
            # Skip sold-out products before URL-pattern filtering
            stock = int(qty)
            if stock == 0:
                logger.debug(f"Skipping sold-out product: {path}")
                continue

            url = self.resolve_url(path)
            slug = path.rsplit("/", 1)[-1].lower()

            # Drop chocolate/matcha/merch slugs.
            if any(excluded in slug for excluded in self._excluded_url_slugs):
                logger.debug(f"Excluding non-coffee product URL: {url}")
                continue

            if self.is_coffee_product_url(url, required_path_patterns=["/coffee/p/"]):
                product_urls.append(url)

        # Deduplicate while preserving order
        product_urls = list(dict.fromkeys(product_urls))
        logger.info(f"Found {len(product_urls)} in-stock coffee product URLs from {store_url}")
        return product_urls

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Pin USD as the store currency (Squarespace geo-pricing guard)."""
        bean.currency = "USD"
        return bean
