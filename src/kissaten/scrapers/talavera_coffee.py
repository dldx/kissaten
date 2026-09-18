"""Talavera Coffee scraper implementation with AI extraction (Squarespace)."""

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
    name="talavera-coffee",
    display_name="Talavera Coffee",
    roaster_name="Talavera Coffee",
    website="https://www.talaveracoffee.com",
    description="Mexican-American specialty coffee roaster and café based in Conroe, Texas, "
    "featuring single-origin Mexican coffees and direct-trade offerings.",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class TalaveraCoffeeScraper(BaseScraper):
    """Scraper for Talavera Coffee (talaveracoffee.com) — a Squarespace storefront.

    Follows the pala_kaffebrenneri.py Squarespace model for product detail
    pages: og:/product: meta tags plus per-variant size/price data parsed from
    the ``<script data-name="static-context">`` JSON, sent to the AI extractor
    in a compact soup.

    The ``/shop`` listing is JS-rendered (no ``<a href>`` product cards in the
    static HTML), but Squarespace embeds the shop grid's product data —
    including ``urlSlug`` and the product-level ``qtyInStock`` — in an escaped
    JSON blob on the page. We parse that blob for URL discovery and stock
    status instead of scraping rendered cards.
    """

    # Non-coffee slugs to exclude: stickers, drinkware, and the origami dripper
    # set (the base class already excludes gift cards, and the Fermentation
    # Project live-cupping event ticket via its "cupping" service pattern).
    # The roaster's-choice sampler set is NOT excluded (tasting-kit flagging is
    # automatic downstream).
    _excluded_url_slugs = [
        "sticker",
        "camper-mug",
        "mug-sticker",
        "origami",
    ]

    def __init__(self, api_key: str | None = None):
        """Initialize Talavera Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Talavera Coffee",
            base_url="https://www.talaveracoffee.com",
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
        """Return the Squarespace shop listing URL."""
        return ["https://www.talaveracoffee.com/shop"]

    @staticmethod
    def _parse_shop_product_blob(page_html: str) -> list[tuple[str, int]]:
        """Extract (url_slug, qty_in_stock) pairs from the shop page's JSON blob.

        Squarespace embeds the shop grid's products as escaped JSON records
        shaped ``{"id":"<24 hex>","title":...,"urlSlug":"<slug>","qtyInStock":<n>}``.
        Variant-level ``qtyInStock`` values appear BEFORE ``urlSlug`` inside the
        same record, so the product-level quantity is taken as the first
        ``qtyInStock`` AFTER the ``urlSlug`` key.

        Args:
            page_html: Raw HTML of the /shop page

        Returns:
            List of (url_slug, product-level qty_in_stock) tuples.
        """
        text = html_module.unescape(page_html)
        records: list[tuple[str, int]] = []
        for chunk in text.split('{"id":"')[1:]:
            slug_match = re.search(r'"urlSlug":"([^"]+)"', chunk)
            if not slug_match:
                continue
            qty_match = re.search(r'"qtyInStock":(\d+)', chunk[slug_match.end() :])
            if qty_match:
                records.append((slug_match.group(1), int(qty_match.group(1))))
        return records

    # Sold-out detection: embedded product JSON quantity check. Squarespace's
    # shop grid data carries the product-level "qtyInStock"; qtyInStock == 0
    # means the product renders with a "Sold Out" badge (verified against the
    # live site's two sold-out coffees), so those slugs are skipped BEFORE
    # coffee-URL filtering. Products sold out with unlimited-quantity flag
    # (9223372036854775807) are treated as in stock.
    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract coffee product URLs from the Squarespace shop page blob.

        Args:
            store_url: URL of the /shop listing page

        Returns:
            List of in-stock product URLs
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        product_urls: list[str] = []
        for slug, qty_in_stock in self._parse_shop_product_blob(str(soup)):
            # Skip sold-out products before URL-pattern filtering
            if qty_in_stock <= 0:
                logger.debug(f"Skipping sold-out product: {slug}")
                continue
            product_urls.append(f"{self.base_url}/shop/p/{slug}")

        product_urls = list(dict.fromkeys(product_urls))

        # Exclude shop-specific non-coffee items: stickers, mugs, dripper set,
        # gift cards (base class) and the live-cupping event ticket (base class
        # "cupping" pattern).
        coffee_urls = [
            url
            for url in product_urls
            if self.is_coffee_product_url(url, required_path_patterns=["/shop/p/"])
            and not any(ex in url.lower() for ex in self._excluded_url_slugs)
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
        if not url or "/shop/p/" not in url:
            return soup
        if soup is None:
            return None

        # Talavera's structured data lives in <head> meta tags. The og:description
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
        regex used by pala_kaffebrenneri doesn't match Talavera's markup (the
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

        Talavera's coffee products are varianted by grind (Wholebean, Ground)
        with per-variant pricing. Surfacing them alongside the meta tags lets
        the AI record the size and price-per-variant accurately.

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
