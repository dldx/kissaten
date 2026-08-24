"""The Forge Coffee Roasters scraper implementation with AI extraction.

The Forge Coffee Roasters (www.forgecoffeeroasters.co.uk) is a Sheffield, UK
roaster hosted on Squarespace (7.1/Brine). Like Echelon and Pala Kaffebrenneri,
the storefront exposes no Shopify products.json endpoint, so we rely on the
Squarespace patterns:

- The shop listing at /store renders its product grid server-side as
  ``div.product-list-item`` cards (Brine template), each containing an
  ``a.product-list-item-link`` to ``/store/p/<slug>``. We extract those
  anchors directly. The literal ``/store/p/`` path pattern is confirmed
  against the live sitemap (28 pages).
- Product pages carry clean og:* / product:* meta tags (og:title,
  og:description, product:price:amount = GBP, product:availability) plus
  per-variant size/price/stock inside ``<script data-name="static-context">``.
- Roast/visual info is captured via Playwright screenshots after dismissing
  the cookie banner and pruning related-product blocks.

Exclusions: brewing equipment, cups, mugs, bowls, planters, filter papers,
scales, jewellery and other accessories (golden-mist-cup, milk-dip-cup,
spring-bowl, aeropress, timemore, ceado-hoop-brewer, …) are dropped as
non-coffee; genuine coffee beans (blends + single origins) are retained.
Sold-out coffees (e.g. Brazil Sitio Da Torre) are kept in the catalogue so
the out-of-stock state is tracked via stock updates.
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
    name="forge",
    display_name="The Forge Coffee Roasters",
    roaster_name="Forge",
    website="https://www.forgecoffeeroasters.co.uk",
    description=(
        "The Forge Coffee Roasters is a Sheffield, South Yorkshire speciality "
        "coffee roaster offering single-origin and blended coffees alongside "
        "brewing equipment."
    ),
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class ForgeScraper(BaseScraper):
    """Scraper for The Forge Coffee Roasters (www.forgecoffeeroasters.co.uk) — Squarespace."""

    def __init__(self, api_key: str | None = None):
        """Initialize The Forge Coffee Roasters scraper."""
        super().__init__(
            roaster_name="Forge",
            base_url="https://www.forgecoffeeroasters.co.uk",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Return the Squarespace shop listing URL.

        The /store page server-renders every product card (Brine template),
        so a single listing page is sufficient (verified 1:1 against the
        live sitemap — all 28 product URLs appear as literal ``/store/p/``
        anchors). The apex ``/store`` path 301s to ``www``, so we use
        the canonical www URL directly.
        """
        return ["https://www.forgecoffeeroasters.co.uk/store"]

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract coffee product URLs from the Squarespace listing page.

        Forge's Brine template renders the product grid server-side as
        ``div.product-list-item`` blocks. Each block contains an
        ``a.product-list-item-link`` whose href is ``/store/p/<slug>``
        (attribute is often unquoted in the raw HTML, e.g.
        ``href=/store/p/las-moritas`` — BeautifulSoup handles that fine, so
        the selector matches regardless of quoting).

        Sold-out products are deliberately kept: they are marked with a
        ``sold-out`` class but still belong to the catalogue, and keeping
        them lets the base scraper emit out-of-stock stock-update diffs.
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        product_urls = []
        for link in soup.select("a[href*='/store/p/']"):
            href = link.get("href")
            if href:
                product_urls.append(self.resolve_url(href))

        product_urls = list(dict.fromkeys(product_urls))

        # Exclude non-coffee: brewing equipment, filter papers, scales,
        # grinders, mugs/cups, bowls/planters and other accessories.
        excluded = [
            "aeropress",
            "ceado",
            "hoop-brewer",
            "brewer",
            "dripper",
            "clever-dripper",
            "timemore",
            "grinder",
            "scales",
            "scale",
            "filters",
            "filter-papers",
            "coffee-server",
            "server",
            "cup",
            "mug",
            "bowl",
            "planter",
            "keepcup",
            "enamel",
            "shot-glass",
            "playing-cards",
            "bracelet",
            "vacuum",
            "storage",
        ]
        coffee_urls = [
            url
            for url in product_urls
            if self.is_coffee_product_url(url, required_path_patterns=["/store/p/"])
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
            translate_to_english=False,  # UK site — already in English
        )

    async def take_screenshot(self, url: str, full_page: bool = True) -> bytes | None:
        """Take screenshot after dismissing the Squarespace cookie banner.

        networkidle can occasionally hang on this host, so on failure we
        degrade gracefully (return None) — the extractor then relies on the
        meta-only HTML soup and never blocks on the screenshot.
        """
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

            # Remove related products section before taking screenshot
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
        if "/store/p/" not in url:
            return soup

        # Forge's structured data lives in <head> meta tags. The og:description
        # carries the roast/name; product:* carries price, currency and
        # availability. The visual/roast info comes from the screenshot.
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

        Squarespace embeds the product's variants (size, price, currency, stock)
        inside a <script data-name="static-context"> as the JSON blob
        "Static.SQUARESPACE_CONTEXT = {...}". We surface those alongside the meta
        tags so the AI can record the size and price-per-variant accurately.
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
        """Hardcode GBP as the store currency.

        Squarespace uses product:price:currency rather than og:price:currency,
        so we force GBP as a final guard.
        """
        bean.currency = "GBP"
        return bean

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup | Tag:
        """No extra pruning needed — meta tags already carried by fetch_page."""
        return soup
