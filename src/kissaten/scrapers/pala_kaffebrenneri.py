"""Pala Kaffebrenneri scraper implementation with AI extraction.

Pala Kaffebrenneri (pala.no) migrated off Squarespace to a custom **Next.js**
storefront on Vercel (verified live 2026-11: ``/butikk`` returns a Next.js
error page, while the catalogue lives at ``https://pala.no/products/coffee``).

The coffee listing page embeds a ``schema.org/ItemList`` JSON-LD block with
one entry per coffee (name + canonical ``/products/<handle>`` URL), so that is
the primary URL source; ``<a href^="/products/">`` links serve as a fallback.
Product pages still emit Squarespace-style ``og:*`` and ``product:price:*`` /
``product:availability`` meta tags plus a ``schema.org/Product`` JSON-LD whose
``offers`` array carries per-variant (size) prices — we leverage the meta tags
and the offers JSON alongside page screenshots to extract CoffeeBean models.
"""

import json
import logging
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)

STORE_URL = "https://pala.no/products/coffee"


@register_scraper(
    name="pala-kaffebrenneri",
    display_name="Pala Kaffebrenneri",
    roaster_name="Pala Kaffebrenneri",
    website="https://pala.no",
    description=(
        "Specialty coffee roaster based in Trondheim, Norway, offering "
        "clean, transparent, and flavor-forward Nordic roasted coffees."
    ),
    requires_api_key=True,
    currency="NOK",
    country="Norway",
    status="available",
)
class PalaKaffebrenneriScraper(BaseScraper):
    """Scraper for Pala Kaffebrenneri (pala.no) — a custom Next.js storefront.

    We lever the product-page meta tags (og:title, og:description,
    product:price:*, product:availability) and the ``schema.org/Product``
    JSON-LD offers array (per-variant size/price) alongside page screenshots
    to extract CoffeeBean models.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Pala Kaffebrenneri scraper."""
        super().__init__(
            roaster_name="Pala Kaffebrenneri",
            base_url="https://pala.no",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Return the Next.js coffee listing (butikk) URL."""
        return [STORE_URL]

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract coffee product URLs from the Next.js listing page.

        The listing page embeds a ``schema.org/ItemList`` JSON-LD block with
        the coffee catalogue; ``<a href^="/products/">`` links are a fallback.
        Cards may carry an "Utsolgt" (sold-out) badge, so any card containing
        that marker is skipped.
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        product_urls: list[str] = []
        seen: set[str] = set()

        def add_url(url: str) -> None:
            normalized = url.split("?")[0].split("#")[0]
            if normalized in seen:
                return
            seen.add(normalized)
            product_urls.append(normalized)

        # Primary source: schema.org/ItemList JSON-LD (one entry per coffee).
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
            except (json.JSONDecodeError, TypeError):
                continue
            if data.get("@type") != "ItemList":
                continue
            for entry in data.get("itemListElement", []):
                url = entry.get("url") if isinstance(entry, dict) else None
                if url and self.is_coffee_product_url(url, required_path_patterns=["/products/"]):
                    add_url(url)

        # Fallback: anchor links into product pages (excluding the listing
        # page itself and non-coffee categories such as /products/utstyr).
        if not product_urls:
            for a in soup.select("a[href^='/products/']"):
                href = a.get("href")
                if not href or not isinstance(href, str):
                    continue
                url = self.resolve_url(href)
                if not self.is_coffee_product_url(url, required_path_patterns=["/products/"]):
                    continue
                if urlparse(url).path.rstrip("/") == urlparse(store_url).path.rstrip("/"):
                    continue
                card_text = " ".join(a.get_text(" ", strip=True).split()).lower()
                if "utsolgt" in card_text:
                    continue
                add_url(url)

        logger.info(f"Found {len(product_urls)} coffee product URLs out of {len(seen)} total from {store_url}")
        return product_urls

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
            translate_to_english=True,  # Norwegian site — translate beans to English
        )

    async def take_screenshot(self, url: str, full_page: bool = True) -> bytes | None:
        """Take screenshot after dismissing the cookie banner."""
        browser = await self._get_browser()
        page = await browser.new_page()

        try:
            signed_headers = self.get_signed_headers(url)
            headers_to_set = {**self.headers, **signed_headers}
            await page.set_extra_http_headers(headers_to_set)

            response = await page.goto(url, timeout=self.timeout * 1000, wait_until="networkidle")

            if not response or not response.ok:
                raise Exception(f"Failed to load page: {response.status if response else 'No response'}")

            # Dismiss cookie banner if present (generic selectors)
            try:
                accept_btn = await page.wait_for_selector(
                    ".sqs-cookie-banner-v2-accept, button.accept, "
                    "[data-testid='cookie-accept'], button:has-text('Godta')",
                    timeout=3000,
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
        """Send the product-page meta tags plus the parsed variant offers to
        the extractor — visual/roast info comes from the page screenshot."""
        soup = await super().fetch_page(*args, **kwargs)
        url = kwargs.get("url") or (args[0] if args else "")
        # Compaction applies to product pages: the Next.js storefront lists them
        # under ``/products/<slug>``, the legacy Squarespace site used
        # ``/butikk/p/<slug>``. Listing/category pages pass through untouched.
        is_product_page = "/products/" in url or "/butikk/p/" in url
        if not is_product_page or urlparse(url).path.rstrip("/") == urlparse(STORE_URL).path.rstrip("/"):
            return soup

        # Pala's structured data lives in <head> meta tags. The og:description
        # carries name/tasting/origin/process/altitude; product:* carries price,
        # currency and availability. The visual/roast info comes from the screenshot.
        compact = BeautifulSoup("<html><head></head><body></body></html>", "html.parser")
        keep_meta = {
            "og:title",
            "og:description",
            "og:url",
            "og:type",
            "og:image",
            "product:price:amount",
            "product:price:currency",
            "product:availability",
        }
        for meta in soup.find_all("meta"):
            key = meta.get("property") or meta.get("itemprop") or meta.get("name")
            if key in keep_meta or meta.get("name") == "description":
                compact.head.append(meta)

        compact.body.append(self._extract_variants(soup))
        description = self._extract_product_description_tag(soup)
        if description is not None:
            compact.body.append(description)
        return compact

    @staticmethod
    def _extract_variants(soup: BeautifulSoup) -> Tag:
        """Parse the schema.org/Product JSON-LD offers array for per-variant price.

        The Next.js storefront embeds a ``<script type="application/ld+json">``
        with ``@type: Product`` whose ``offers`` array lists each packaging
        variant (name, price, currency, availability, sku). We surface those
        alongside the meta tags so the AI can record the size and
        price-per-variant accurately.
        """
        container = BeautifulSoup("<div></div>", "html.parser").div
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
            except (json.JSONDecodeError, TypeError):
                continue
            if data.get("@type") != "Product":
                continue

            offers = data.get("offers") or []
            if not isinstance(offers, list) or not offers:
                return container

            lines = ["Variants:"]
            for offer in offers:
                if not isinstance(offer, dict):
                    continue
                size = offer.get("name") or "n/a"
                price = offer.get("price")
                currency = offer.get("priceCurrency")
                availability = str(offer.get("availability") or "")
                stock = "instock" if availability.endswith("InStock") else "unknown"
                sku = offer.get("sku") or ""
                line = f"- {size} | Price: {price} {currency} | Stock: {stock}"
                if sku:
                    line += f" | SKU: {sku}"
                lines.append(line)
            container.string = "\n".join(lines)
            return container

        return container

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Hardcode NOK as the store currency (Pala sells exclusively in NOK)."""
        bean.currency = "NOK"
        return bean

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup | Tag:
        """No extra pruning needed — meta tags already carried by fetch_page."""
        return soup
