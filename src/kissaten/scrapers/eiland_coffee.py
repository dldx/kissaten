"""Eiland Coffee Roasters scraper implementation with AI extraction (Squarespace)."""

import json
import logging

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="eiland-coffee",
    display_name="Eiland Coffee Roasters",
    roaster_name="Eiland Coffee Roasters",
    website="https://www.eilandcoffee.com",
    description="Specialty coffee roaster based in Richardson/Allen, Texas, "
    "offering single-origin coffees, blends, and coffee education.",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class EilandCoffeeScraper(BaseScraper):
    """Scraper for Eiland Coffee Roasters (eilandcoffee.com) — a Squarespace storefront.

    Follows the pala_kaffebrenneri.py Squarespace model: server-rendered listing
    cards, product-page meta tags (og:title, og:description, product:price:*,
    product:availability) plus per-variant size/price data parsed from the
    ``<script data-name="static-context">`` JSON, sent to the AI extractor in a
    compact soup.

    Eiland's product pages live under ``/coffee-stock-room/<slug>`` (not the
    usual ``/shop/p/``), and its cards use the Squarespace 7.0 ``div.product-block``
    structure. Product detail pages are fetched from ``/shop`` (main coffee
    list) and ``/fermentationproject`` (Fermentation Project kits page).
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Eiland Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Eiland Coffee Roasters",
            base_url="https://www.eilandcoffee.com",
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
        """Return the Squarespace listing URLs (main shop + Fermentation Project page)."""
        return [
            "https://www.eilandcoffee.com/shop",
            "https://www.eilandcoffee.com/fermentationproject",
        ]

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract coffee product URLs from the Squarespace listing page.

        # Sold-out detection: text check on each product card. Squarespace marks
        # sold-out products with "Sold Out" on the card (the site's
        # customSoldOutText), so we check each div.product-block card's own text
        # (never a whole-page search — the marker also appears in embedded
        # settings JSON) and skip those cards BEFORE coffee-URL filtering.
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        product_urls: list[str] = []
        seen: set[str] = set()
        for link in soup.select("a[href*='/coffee-stock-room/']"):
            href = link.get("href")
            if not href or not isinstance(href, str):
                continue

            # Card-level sold-out check: walk up to the enclosing product block
            block = link.find_parent(class_=lambda c: bool(c) and "product-block" in c)
            if block is not None:
                card_text = " ".join(block.get_text(" ", strip=True).split()).lower()
                if "sold out" in card_text or "out of stock" in card_text:
                    logger.debug(f"Skipping sold-out product: {href}")
                    continue

            full_url = self.resolve_url(href.split("?")[0].split("#")[0])
            if full_url not in seen:
                seen.add(full_url)
                product_urls.append(full_url)

        # Exclude non-coffee items: gift cards (base class) and the live-cupping
        # event ticket (a service, excluded by the base class "cupping" pattern).
        # The Fermentation Project kit and the blind-tasting-set are NOT
        # excluded (tasting-kit flagging is automatic downstream).
        coffee_urls = [
            url
            for url in product_urls
            if self.is_coffee_product_url(url, required_path_patterns=["/coffee-stock-room/"])
        ]
        logger.info(f"Found {len(coffee_urls)} coffee product URLs out of {len(product_urls)} total from {store_url}")
        return coffee_urls

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction."""
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

    async def fetch_page(self, *args, **kwargs):
        """Send the product-page meta tags plus the parsed size/price variants to
        the extractor."""
        soup = await super().fetch_page(*args, **kwargs)
        url = kwargs.get("url") or (args[0] if args else "")
        if not url or "/coffee-stock-room/" not in url:
            return soup
        if soup is None:
            return None

        # Eiland's structured data lives in <head> meta tags. The og:description
        # carries name/tasting/origin/process; product:* carries price,
        # currency and availability.
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
                compact.head.append(meta)  # type: ignore[union-attr]

        variants = self._extract_variants(soup)
        if variants is not None:
            compact.body.append(variants)  # type: ignore[union-attr]
        return compact

    @staticmethod
    def _parse_static_context(soup: BeautifulSoup) -> dict | None:
        """Parse the Squarespace static-context script into a dict.

        Squarespace embeds the site context as
        ``Static = window.Static || {}; Static.SQUARESPACE_CONTEXT = {...};``
        inside ``<script data-name="static-context">``. The closing-semicolon
        regex used by pala_kaffebrenneri doesn't match Eiland's markup (the
        script contains trailing statements), so we brace-match the JSON blob
        directly instead.

        Args:
            soup: BeautifulSoup object of the product page

        Returns:
            Parsed context dict, or None if absent/unparseable.
        """
        script = soup.find("script", {"data-name": "static-context"})
        if script is None:
            return None

        blob = script.string or script.get_text() or ""
        marker = "Static.SQUARESPACE_CONTEXT = "
        marker_idx = blob.find(marker)
        if marker_idx == -1:
            return None

        start = blob.find("{", marker_idx)
        if start == -1:
            return None

        depth = 0
        for pos in range(start, len(blob)):
            char = blob[pos]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(blob[start : pos + 1])
                    except json.JSONDecodeError:
                        return None
        return None

    @classmethod
    def _extract_variants(cls, soup: BeautifulSoup) -> Tag | None:
        """Build a text node describing the product's per-variant size/price.

        Eiland's coffee products are varianted by grind (Whole Bean, Pour
        Over, Drip, French Press, Espresso, Aeropress) with per-variant
        pricing. Surfacing them alongside the meta tags lets the AI record the
        size and price-per-variant accurately.

        Args:
            soup: BeautifulSoup object of the product page

        Returns:
            A <div> Tag with variant lines, or None when no variants exist.
        """
        data = cls._parse_static_context(soup)
        if not data:
            return None

        product = data.get("product") or {}
        variants = product.get("variants") or []
        if not variants:
            return None

        lines = ["Variants:"]
        for variant in variants:
            attrs = variant.get("attributes") or {}
            size = "; ".join(str(val) for val in attrs.values()) or "n/a"
            price = (variant.get("price") or {}).get("decimalValue")
            currency = (variant.get("price") or {}).get("currencyCode")
            if not currency:
                # Squarespace variant JSON often omits the currency; the
                # product:price:currency og-meta on the page carries it.
                meta = soup.select_one('meta[property="product:price:currency"]')
                currency = meta.get("content") if meta else None
            stock = variant.get("stock") or {}
            stock_state = "instock" if stock.get("unlimited") else "unknown"
            lines.append(f"- Size: {size} | Price: {price} {currency} | Stock: {stock_state}")

        container = BeautifulSoup("<div></div>", "html.parser").div
        container.string = "\n".join(lines)  # type: ignore[union-attr]
        return container

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Pin USD as the store currency (Squarespace emits product:price:currency
        but pin it here as a final guard against the default-GBP fallback)."""
        bean.currency = "USD"
        return bean
