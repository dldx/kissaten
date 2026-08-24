"""51 Degrees North scraper implementation with AI extraction (Squarespace).

51 Degrees North (www.51degreesnorthcoffee.com) is a Squarespace storefront
selling single-origin coffee. Like pala.no, product pages expose the
``Static.SQUARESPACE_CONTEXT`` JSON blob (per-variant size/price) and
``product:*`` meta tags, so ``fetch_page`` prunes the product page to those
meta tags plus the parsed variants, and visual/roast info comes from a clean
full-page screenshot (cookie banner dismissed, related products removed).
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
    name="51-degrees-north",
    display_name="51 Degrees North",
    roaster_name="51 Degrees North",
    website="https://www.51degreesnorthcoffee.com",
    description=(
        "Specialty coffee roaster based in North Devon, England, sourcing "
        "exceptional single-origin coffees."
    ),
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class FiftyOneDegreesNorthScraper(BaseScraper):
    """Scraper for 51 Degrees North (51degreesnorthcoffee.com) — Squarespace.

    The storefront uses the same Squarespace ``Static.SQUARESPACE_CONTEXT``
    static-context structure as pala.no, so parsing is identical.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize 51 Degrees North scraper."""
        super().__init__(
            roaster_name="51 Degrees North",
            base_url="https://www.51degreesnorthcoffee.com",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Return the Squarespace single-origin coffee listing URL."""
        return ["https://www.51degreesnorthcoffee.com/single-origin-coffee"]

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract coffee product URLs from the Squarespace listing page.

        # Sold-out detection: card-level text check. Squarespace marks
        # sold-out products with "sold out" on the card, so we skip those cards
        # before filtering through the coffee URL check.
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        product_urls = []
        for item in soup.select("div.product-list-item, section.product-list-item, a.product-list-item-link"):
            card_text = " ".join(item.get_text(" ", strip=True).split()).lower()
            if "sold out" in card_text:
                continue

            if item.name == "a":
                href = item.get("href")
                if href:
                    product_urls.append(self.resolve_url(href))
            else:
                link = item.find("a", class_="product-list-item-link") or item.find("a", href=True)
                if link and link.get("href"):
                    product_urls.append(self.resolve_url(link["href"]))

        product_urls = list(dict.fromkeys(product_urls))

        # Genuine non-coffee exclusion only (this listing is single-origin
        # coffee, so no services/equipment appear; no tasting-kit tokens added).
        coffee_urls = [
            url
            for url in product_urls
            if self.is_coffee_product_url(url, required_path_patterns=["/single-origin-coffee/p/"])
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
            translate_to_english=False,  # English site — no translation
        )

    async def take_screenshot(self, url: str, full_page: bool = True) -> bytes | None:
        """Take screenshot after dismissing the Squarespace cookie banner."""
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
        if "/single-origin-coffee/p/" not in url:
            return soup

        # Keep only the structured product metadata that will feed extraction.
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

        Squarespace embeds the product's variants inside a
        ``<script data-name="static-context">`` as the JSON blob
        "Static.SQUARESPACE_CONTEXT = {...}". We surface those alongside the
        meta tags so the AI can record the size and price-per-variant.
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
        """Hardcode GBP as the store currency (final guard)."""
        bean.currency = "GBP"
        return bean
