"""Fika Coffee Roasters scraper implementation with AI extraction.

Fika Coffee Roasters (www.fikacoffeeroasters.co.uk) is a County Durham, UK
roaster hosted on Squarespace 7.1. Like Pala Kaffebrenneri and Blue Hour
Coffee, the storefront exposes no Shopify products.json endpoint, so we rely
on the Squarespace patterns:

- Product detail pages live at ``/coffee/p/<slug>``, but some handles carry
  extra path segments (e.g. ``/coffee/p/brazil/bomjesus``,
  ``/coffee/p/uganda/kyondo/natural``, ``/coffee/p/rwanda/peaberry``). The
  /coffee listing renders products client-side and our probe found no
  ``/p/`` fullUrls in its ``data-context`` blob, so we enumerate the coffee
  product URLs from the static ``sitemap.xml`` instead (the authoritative
  source, matching only ``/coffee/p/...`` paths and excluding equipment
  ``/equipment/p/...``).
- Product pages carry clean og:* / product:* meta tags (og:title,
  og:description, product:price:amount = GBP, product:availability) plus
  per-variant size/price/stock inside ``<script data-name="static-context">``.
- Roast/visual info is captured via Playwright screenshots after dismissing
  the cookie banner and pruning related-product blocks.

Exclusions: the ``/coffee/p/`` subscriptions (monthly-subscription,
bi-weekly-subscription) and the digital gift card (fika-digital-gift-card)
are dropped; equipment/merch never appears under /coffee/p/ so the sitemap
path filter handles it. The ``coffee-fika-sample-pack`` is a tasting kit and
is deliberately retained (flag-don't-exclude) so the base scraper's
``_apply_product_flags`` marks it ``is_tasting_kit`` / ``requires_review``
into the admin review queue. Sold-out coffees (e.g. Colombia Geisha Rio
Bamisa) are kept in the catalogue so the out-of-stock state is tracked via
stock-update diffs.
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
    name="fika",
    display_name="Fika",
    roaster_name="Fika",
    website="https://www.fikacoffeeroasters.co.uk",
    description=(
        "Fika Coffee Roasters is a speciality coffee roaster based in "
        "County Durham, UK, offering single-origin, seasonal and espresso "
        "coffees roasted to order."
    ),
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class FikaScraper(BaseScraper):
    """Scraper for Fika Coffee Roasters (www.fikacoffeeroasters.co.uk) — Squarespace."""

    def __init__(self, api_key: str | None = None):
        """Initialize Fika Coffee Roasters scraper."""
        super().__init__(
            roaster_name="Fika",
            base_url="https://www.fikacoffeeroasters.co.uk",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Return the sitemap URL used for product discovery.

        Squarespace 7.1 renders the /coffee listing client-side, and our probe
        found no ``/p/`` fullUrls in its ``data-context`` blob. The static
        ``sitemap.xml`` is the reliable source: every coffee product appears
        as a ``/coffee/p/<slug>`` entry (including multi-segment handles), and
        equipment/merch live under ``/equipment/p/`` so they never match the
        coffee path filter.
        """
        return ["https://www.fikacoffeeroasters.co.uk/sitemap.xml"]

    # Non-coffee handles that appear under /coffee/p/: the two subscription
    # products and the digital gift card. The sample pack is intentionally
    # NOT in this list (tasting kit -> flag-don't-exclude).
    _excluded_coffee_slugs = [
        "subscription",
        "subscriptions",
        "gift-card",
        "giftcard",
        "gift_card",
    ]

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract coffee product URLs from the sitemap.xml.

        Squarespace publishes a static sitemap with one ``<loc>`` per page.
        We keep only the ``/coffee/p/`` entries (which handles multi-segment
        slugs such as ``/coffee/p/uganda/kyondo/natural``), then drop the
        subscriptions and gift card. Sold-out coffees are kept so the base
        scraper can emit out-of-stock stock-update diffs.
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            logger.error(f"Failed to fetch sitemap: {store_url}")
            return []

        product_urls: list[str] = []
        for loc in soup.select("loc"):
            url = loc.get_text(strip=True)
            if not url:
                continue
            # Only coffee product detail URLs under /coffee/p/.
            if not self.is_coffee_product_url(url, required_path_patterns=["/coffee/p/"]):
                continue
            # Exclude subscriptions and gift cards (coffee handle set).
            url_lower = url.lower()
            if any(slug in url_lower for slug in self._excluded_coffee_slugs):
                logger.debug(f"Excluding non-coffee product URL: {url}")
                continue
            product_urls.append(url)

        # Deduplicate while preserving order.
        seen: set[str] = set()
        unique_urls: list[str] = []
        for url in product_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        logger.info(f"Found {len(unique_urls)} coffee product URLs from sitemap")
        return unique_urls

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
        """Take screenshot after dismissing Squarespace cookie banner."""
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
        # Product pages live at /coffee/p/<slug> (path detection is a plain
        # "/p/" substring so multi-segment handles like /coffee/p/uganda/kyondo
        # are matched too). The sitemap itself must not be compacted.
        if "/p/" not in url:
            return soup

        # Fika's structured data lives in <head> meta tags. The og:description
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
