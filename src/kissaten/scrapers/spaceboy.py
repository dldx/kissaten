"""Spaceboy Coffee scraper implementation with AI extraction.

Spaceboy Coffee (spaceboycoffee.co.uk) is a micro speciality coffee roastery in
Edinburgh, UK, hosted on Squarespace Commerce. Product pages live under the
``/shop/p/`` path and carry Squarespace's standard ``og:*`` / ``product:*`` meta
tags plus a ``Static.SQUARESPACE_CONTEXT`` blob in a
``<script data-name="static-context">`` tag holding the per-variant size/price
and stock.

Unlike a plain Squarespace listing, Spaceboy does *not* emit ``/shop/p/``
anchors in the DOM of the shop page — the coffee catalog is embedded as escaped
JSON in the ``data-context`` attribute of the ``div[data-controller=ProductList]``
element. ``_extract_product_urls_from_store`` parses that blob to enumerate the
products (skipping any that are sold out and excluding the merch t-shirt).
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
    name="spaceboy",
    display_name="Spaceboy Coffee",
    roaster_name="Spaceboy Coffee",
    website="https://spaceboycoffee.co.uk",
    description=(
        "Spaceboy Coffee is a micro speciality coffee roastery in Edinburgh, UK, "
        "roasting single origin coffees, blends and a decaf, plus occasional "
        "experimental and rare-varietal lots."
    ),
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class SpaceboyCoffeeScraper(BaseScraper):
    """Scraper for Spaceboy Coffee (spaceboycoffee.co.uk) — a Squarespace storefront.

    Squarespace exposes the product price via ``product:price:currency`` rather
    than ``og:price:currency`` (which the base ``_extract_currency_from_html``
    sniffs for), so GBP is locked up front and surfaced as extra context to the
    AI via the meta-only soup plus the parsed variants text.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Spaceboy Coffee scraper."""
        super().__init__(
            roaster_name="Spaceboy Coffee",
            base_url="https://spaceboycoffee.co.uk",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

        # Squarespace emits product:price:currency (not og:price:currency) so
        # the base currency sniffer would miss it. Lock GBP up front and stop
        # the base from re-detecting currency from product pages.
        self.store_currency = "GBP"
        self._currency_detected = True

    async def get_store_urls(self) -> list[str]:
        """Return the Squarespace shop listing URL."""
        return ["https://spaceboycoffee.co.uk/shop"]

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract coffee product URLs from the Squarespace listing page.

        Spaceboy embeds the whole coffee catalog as escaped JSON in the
        ``data-context`` attribute of the ``div[data-controller=ProductList]``
        element (there are no ``/shop/p/`` anchors in the listing DOM). Each
        item carries its ``fullUrl`` and a ``soldOut`` flag; the single merch
        item (an isometric t-shirt) is excluded below.
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        product_urls = []
        for container in soup.select("div[data-controller=ProductList], .ProductList-item"):
            ctx = container.get("data-context") if isinstance(container, Tag) else None
            if ctx:
                try:
                    data = json.loads(ctx)
                except (json.JSONDecodeError, TypeError):
                    data = None
                if data:
                    for item in data.get("items") or []:
                        full_url = item.get("fullUrl")
                        sold_out = bool(item.get("soldOut"))
                        if full_url and not sold_out:
                            product_urls.append(self.resolve_url(str(full_url)))

            # Fallback: product-card DOM anchors (older Squarespace themes).
            for a in container.find_all("a", href=True):
                if "/shop/p/" in a["href"]:
                    product_urls.append(self.resolve_url(a["href"]))

        # Also catch any plain /shop/p/ anchors anywhere on the listing page.
        for a in soup.select("a[href*='/shop/p/']"):
            product_urls.append(self.resolve_url(a["href"]))

        product_urls = list(dict.fromkeys(product_urls))

        # Exclude the single merch item (isometric t-shirt) plus any other
        # non-coffee shop items (subscriptions, brewing hardware, gift cards).
        # Samplers / tasting kits are intentionally NOT excluded — they flow
        # through and are flagged is_tasting_kit for admin review.
        excluded = ["shirt", "tshirt", "t-shirt", "merch", "hoodie", "mug", "cap", "gift-card"]
        coffee_urls = [
            url
            for url in product_urls
            if self.is_coffee_product_url(url, required_path_patterns=["/shop/p/"])
            and not any(ex in url.lower() for ex in excluded)
        ]
        logger.info(
            f"Found {len(coffee_urls)} coffee product URLs out of {len(product_urls)} total from {store_url}"
        )
        return coffee_urls

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
            translate_to_english=False,  # English store — no translation needed
        )

    async def take_screenshot(self, url: str, full_page: bool = True) -> bytes | None:
        """Take a clean screenshot (cookie banner dismissed, related products pruned)."""
        browser = await self._get_browser()
        page = await browser.new_page()

        try:
            signed_headers = self.get_signed_headers(url)
            headers_to_set = {**self.headers, **signed_headers}
            await page.set_extra_http_headers(headers_to_set)

            response = await page.goto(url, timeout=self.timeout * 1000, wait_until="networkidle")

            if not response or not response.ok:
                raise Exception(f"Failed to load page: {response.status if response else 'No response'}")

            # Dismiss Squarespace cookie banner if present
            try:
                accept_btn = await page.wait_for_selector(
                    ".sqs-cookie-banner-v2-accept, button.accept", timeout=3000
                )
                if accept_btn:
                    await accept_btn.click()
                    await page.wait_for_timeout(1000)
            except Exception as e:
                logger.debug(f"No cookie banner dismissed: {e}")

            # Remove related-products sections before capturing the screenshot
            try:
                await page.evaluate("""() => {
                    const els = document.querySelectorAll('div.product-related-products, .related-products');
                    els.forEach(el => el.remove());
                }""")
            except Exception as e:
                logger.debug(f"Could not remove related products section: {e}")

            # Trigger scroll for lazy-loaded assets
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1000)
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(500)

            return await page.screenshot(full_page=full_page, type="png")

        except Exception as e:
            logger.error(f"Failed to take screenshot of {url}: {e}")
            return None

        finally:
            await page.close()

    async def fetch_page(self, *args, **kwargs):
        """Send the product-page meta tags plus the parsed size/price variants to
        the extractor — visual/roast info comes from the page screenshot."""
        soup = await super().fetch_page(*args, **kwargs)
        url = kwargs.get("url") or (args[0] if args else "")
        if "/shop/p/" not in url:
            return soup

        # Keep only the Squarespace product meta tags (og:* and product:*) plus
        # the parsed per-variant size/price text so the AI has the full set of
        # structured facts without the rest of the page bloating the prompt.
        compact = BeautifulSoup("<html><head></head><body></body></html>", "html.parser")
        keep_meta = {
            "og:title", "og:description", "og:url", "og:type",
            "product:price:amount", "product:price:currency", "product:availability",
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

        Squarespace embeds the product's variants (grind, roast profile, weight,
        price, currency, stock) inside a <script data-name="static-context"> as the
        JSON blob "Static.SQUARESPACE_CONTEXT = {...}". We surface those alongside
        the meta tags so the AI can record the size and price-per-variant accurately.
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
            line = f"- Size: {size} | Price: {price} {currency} | Stock: {stock}"
            lines.append(line)
        container.string = "\n".join(lines)
        return container

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Hardcode GBP as the store currency (Squarespace uses product:price:currency)."""
        bean.currency = "GBP"
        return bean

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup | Tag:
        """No extra pruning needed — meta tags already carried by fetch_page."""
        return soup
