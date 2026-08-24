"""Fortitude Coffee Roasters scraper implementation with AI extraction.

Fortitude Coffee Roasters (www.fortitudecoffee.com) is an Edinburgh-based
specialty coffee roaster (est. 2014) hosted on Squarespace (Template 7.1).
Like Echelon Coffee Roasters and Pala Kaffebrenneri, the storefront exposes
no Shopify products.json endpoint, so we rely on the Squarespace patterns:

- The SHOP listing at /coffee renders its product grid server-side as
  ``<div class="summary-item">`` cards (Squarespace 7.1 summary gallery), each
  containing ``a[href*='/webshop/p/']`` links to ``/webshop/p/<slug>``.
  There is no ``data-context`` JSON blob on this listing, so we extract the
  anchors directly (verified live: 10 product URLs). Product URLs stay at
  the ``/webshop/p/<slug>`` form.
- Product pages carry clean og:* / product:* meta tags (og:title,
  og:description, product:price:amount = GBP, product:availability) plus
  per-variant size/price/stock inside ``<script data-name="static-context">``
  (``Static.SQUARESPACE_CONTEXT.product.variants``).
- Roast/visual info is captured via Playwright screenshots after dismissing
  the cookie banner and pruning related-product blocks.

Notes:
- The bare domain (fortitudecoffee.com) can time out from some clients/UAs;
  always use the www subdomain and a browser-like User-Agent, with the base
  scraper's retry/backoff for resilience.
- Sold-out coffees (e.g. FINCA MARACAY) are kept in the catalogue so the
  out-of-stock state is tracked via stock updates; the listing marks them
  with a ``summary-product-status`` badge but they still belong to the shop.
- Subscriptions live at /start and /manage (outside the /coffee listing);
  they are excluded by URL pattern.
- No tasting kits are expected on this store; if any appear they flow through
  the base ``_apply_product_flags`` review pipeline unchanged.
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

# Browser-like UA: fortitudecoffee.com can be picky about default clients.
_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


@register_scraper(
    name="fortitude",
    display_name="Fortitude Coffee Roasters",
    roaster_name="Fortitude",
    website="https://www.fortitudecoffee.com",
    description=(
        "Fortitude Coffee Roasters is an Edinburgh specialty coffee roastery "
        "and cafés (roastery + 2 cafés, est. 2014), offering small-batch "
        "single-origin coffees and an espresso blend roasted in Edinburgh."
    ),
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class FortitudeScraper(BaseScraper):
    """Scraper for Fortitude Coffee Roasters (www.fortitudecoffee.com) — Squarespace."""

    def __init__(self, api_key: str | None = None):
        """Initialize Fortitude Coffee Roasters scraper."""
        super().__init__(
            roaster_name="Fortitude",
            base_url="https://www.fortitudecoffee.com",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            custom_headers={"User-Agent": _BROWSER_UA},
        )

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Return the Squarespace shop listing URL.

        The /coffee page server-renders every product card (Squarespace 7.1
        summary gallery), so a single listing page is sufficient (verified
        1:1: exactly 10 product anchors). Subscriptions (/start, /manage)
        live outside /coffee and are never reached.
        """
        return ["https://www.fortitudecoffee.com/coffee"]

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract coffee product URLs from the Squarespace listing page.

        Fortitude's 7.1 template renders the shop server-side as ``.summary-item``
        blocks whose anchors point at ``/webshop/p/<slug>`` directly. There is
        no ``data-context`` JSON blob on this page (unlike Blue Hour), so we
        parse the anchors directly.

        Sold-out products are deliberately kept: they are marked on the card
        (a ``summary-product-status`` element reading "Sold out") but still
        belong to the catalogue, and keeping them lets the base scraper emit
        out-of-stock stock-update diffs.
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        product_urls = []
        for link in soup.select("a[href*='/webshop/p/']"):
            href = link.get("href")
            if href:
                product_urls.append(self.resolve_url(href))

        product_urls = list(dict.fromkeys(product_urls))

        # Exclude non-coffee: subscriptions and subscription management pages.
        # Coffee beans (filter + espresso) are retained, incl. sold-out ones.
        excluded = [
            "subscription",
            "subscribe",
            "/start",
            "/manage",
            "gift-card",
            "giftcard",
            "gift_card",
            "v60",
            "grinder",
            "filters",
            "merch",
        ]
        coffee_urls = [
            url
            for url in product_urls
            if self.is_coffee_product_url(url, required_path_patterns=["/webshop/p/"])
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
        """Take screenshot after dismissing Squarespace cookie banner.

        If ``networkidle`` never settles (a known Squarespace behaviour on some
        pages), the timeout raises and we return None — the AI extraction then
        falls back to the meta-only HTML, so a screenshot failure never blocks
        the scrape.
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
        if "/webshop/p/" not in url or not soup:
            return soup

        # Fortitude's structured data lives in <head> meta tags. The og:description
        # carries name/tasting/origin/process/altitude; product:* carries price,
        # currency and availability. The visual/roast info comes from the screenshot.
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
            stock = "instock" if (v.get("stock") or {}).get("unlimited") else "outofstock"
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
