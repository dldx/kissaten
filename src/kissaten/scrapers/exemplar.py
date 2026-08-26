"""Exemplar Coffee scraper implementation with AI-powered extraction.

Exemplar (exemplarcoffee.com) is a small UK "coffee roasting and research
project" running on Squarespace. The store has no Shopify products.json (404)
and no WooCommerce API; the live catalogue lives on the single ``/shop``
listing page. Product cards are ``div.product-list-item`` containers (Squarespace
marks sold-out cards with a ``sold-out`` class) whose links point to
``/shop/p/<slug>`` detail pages. Product detail pages carry Squarespace's
``og:*`` / ``product:*`` meta tags (og:title, og:description,
product:price:amount, product:price:currency, product:availability) plus the
per-variant size/price/stock JSON inside a ``<script data-name="static-context">``,
so we narrow product-page soup to those meta tags + parsed variants for cheap
AI extraction. The store prices in GBP (product:price:currency = GBP).
"""

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
    name="exemplar",
    display_name="Exemplar Coffee",
    roaster_name="Exemplar Coffee",
    website="https://www.exemplarcoffee.com",
    description=(
        "UK speciality coffee roasting and research project running on Squarespace "
        "(whole-bean coffees plus a quarterly research magazine/subscription)."
    ),
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class ExemplarScraper(BaseScraper):
    """Scraper for Exemplar Coffee (exemplarcoffee.com) — a Squarespace storefront."""

    def __init__(self, api_key: str | None = None):
        """Initialize the Exemplar scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Exemplar Coffee",
            base_url="https://www.exemplarcoffee.com",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        # Squarespace emits product:price:currency (not og:price:currency nor a
        # Shopify.currency object), so the base-class currency detection never
        # fires. Pin GBP up front; postprocess_extracted_bean re-applies it as a
        # final guard.
        self.store_currency = "GBP"
        self._currency_detected = True

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Return the Squarespace shop listing URL."""
        return ["https://www.exemplarcoffee.com/shop"]

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract coffee product URLs from the Squarespace /shop listing page.

        # Sold-out detection: class check. Squarespace marks sold-out products
        # with a ``sold-out`` class on the ``div.product-list-item`` card, so we
        # skip those cards before touching the link. Non-bean items (the
        # quarterly research magazine issues and the quarterly subscription) are
        # excluded at the link level — they are genuine non-coffee products, not
        # coffee sampler/taster kits, so nothing is flagged for review.
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        product_urls: list[str] = []
        seen: set[str] = set()
        for item in soup.select("div.product-list-item"):
            classes = item.get("class", [])
            if "sold-out" in classes:
                continue
            link = item.select_one("a.product-list-item-link")
            if not link:
                continue
            href = link.get("href")
            if not href or not isinstance(href, str):
                continue
            full_url = self.resolve_url(href)
            if self.is_coffee_product_url(full_url, required_path_patterns=["/shop/p/"]) and full_url not in seen:
                seen.add(full_url)
                product_urls.append(full_url)

        # The /shop page also carries the quarterly print-magazine products and
        # the "Quarterly Subscription" (a coffee subscription, already dropped by
        # the base "subscription" pattern). Drop the magazine issues — they are
        # research publications, not coffee beans.
        excluded = ["magazine", "vol-", "iss-", "volume", "issue"]
        coffee_urls = [url for url in product_urls if not any(ex in url.lower() for ex in excluded)]
        logger.info(f"Found {len(coffee_urls)} coffee product URLs out of {len(product_urls)} total from {store_url}")
        return coffee_urls

    async def _scrape_new_products(self, product_urls: list[str], use_optimized_mode: bool = False) -> list[CoffeeBean]:
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
            translate_to_english=False,  # English site
        )

    async def fetch_page(self, *args, **kwargs):
        """Send the product-page meta tags plus the parsed size/price variants.

        Squarespace product pages embed all the structured facts (name, tasting
        notes, origin, price, currency, availability, per-variant size/price) in
        <head> meta tags and the static-context variants JSON, so we narrow
        product detail pages to just those and leave the listing page untouched.
        """
        soup = await super().fetch_page(*args, **kwargs)
        url = kwargs.get("url") or (args[0] if args else "")
        if "/shop/p/" not in url:
            return soup

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
        "Static = window.Static || {}; Static.SQUARESPACE_CONTEXT = {...}". We
        surface those alongside the meta tags so the AI records size/price
        accurately. Uses JSONDecoder.raw_decode to handle the trailing JS that
        sometimes follows the assignment.
        """
        container = BeautifulSoup("<div></div>", "html.parser").div
        script = soup.find("script", {"data-name": "static-context"})
        if script is None:
            return container
        blob = script.string or script.get_text() or ""

        marker = blob.find("Static.SQUARESPACE_CONTEXT =")
        obj_start = blob.find("{", marker if marker >= 0 else 0)
        data = None
        if obj_start >= 0:
            try:
                data, _ = json.JSONDecoder().raw_decode(blob[obj_start:])
            except json.JSONDecodeError:
                data = None
        if not data:
            # Fallback to the reference regex used by other Squarespace scrapers.
            match = re.search(r"Static\.SQUARESPACE_CONTEXT\s*=\s*(\{.*?\})\s*;", blob, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                except json.JSONDecodeError:
                    data = None

        product = (data or {}).get("product") or {}
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
            line = f"- Size: {size} | Price: {price} {currency} | Stock: {stock}"
            lines.append(line)
        container.string = "\n".join(lines)
        return container

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Hardcode GBP as the store currency (Squarespace does not emit og:price:currency)."""
        bean.currency = "GBP"
        return bean
