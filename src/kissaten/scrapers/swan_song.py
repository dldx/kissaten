"""Swan Song Coffee Roasters scraper implementation with AI extraction.

Swan Song Coffee Roasters (www.swansong.coffee) is a solo-operated,
Squarespace-hosted roaster in Salford, Manchester (trading as One Percent
Coffee Limited). Products live at ``/coffee/p/...`` and carry the standard
Squarespace product-page meta tags (``og:title``, ``og:description``,
``product:price:*``, ``product:availability``) plus a ``static-context`` JSON
blob with per-variant size/price/currency/stock.

Discovery crawls the ``/coffee`` listing and keeps whole-bean coffee products
only, skipping sold-out cards in the listing markup (``product-mark sold-out``).
Curated samplers/taster-packs are not excluded — they are extracted and flagged
for review by the base tasting-kit pipeline.
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
    name="swan-song",
    display_name="Swan Song Coffee Roasters",
    roaster_name="Swan Song Coffee Roasters",
    website="https://www.swansong.coffee",
    description=(
        "Solo-operated specialty coffee roaster based in Salford, Manchester, "
        "paving their own path with seasonal single-origin whole-bean coffees "
        "(Brazil, Colombia, Ethiopia, Rwanda, Tanzania, Bolivia, Panama, decaf)."
    ),
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class SwanSongScraper(BaseScraper):
    """Scraper for Swan Song Coffee Roasters (www.swansong.coffee) — a Squarespace storefront.

    We leverage the Squarespace product-page meta tags (og:title, og:description,
    product:price:*, product:availability) and static-context variants JSON
    alongside page screenshots to extract CoffeeBean models.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Swan Song Coffee Roasters scraper."""
        super().__init__(
            roaster_name="Swan Song Coffee Roasters",
            base_url="https://www.swansong.coffee",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        # The store prices exclusively in GBP and emits ``product:price:currency``
        # (not ``og:price:currency``), so pin the currency up front and skip
        # geo-detection.
        self.store_currency = "GBP"
        self._currency_detected = True

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Return the Squarespace shop (/coffee) listing URL."""
        return ["https://www.swansong.coffee/coffee"]

    def _get_excluded_url_patterns(self) -> list[str]:
        """Add Swan Song-specific non-coffee exclusions on top of the base set.

        The base list already drops generic equipment/merch/service patterns
        (hario, v60, grinder, subscription, gift-card, ...). Swan Song sells
        only coffee beans today, but we add a few defensive handles in case
        merchandise/subscriptions are ever added to the same listing.
        """
        return super()._get_excluded_url_patterns() + [
            "apparel",  # any future clothing/merch
            "merch",
            "merchandise",
        ]

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract whole-bean coffee product URLs from the Squarespace listing page.

        Squarespace renders each product card with a ``.product-list-item-link``
        anchor pointing at ``/coffee/p/<slug>`` and a sold-out ``.product-mark
        .sold-out`` "Sold Out" badge on unavailable cards.

        We detect sold-out by walking from each sold-out mark up to its nearest
        product anchor rather than by reading card text: this theme (like many
        Squarespace templates) emits heavily nested/unclosed anchors that make
        ``get_text()`` on a card leak into its neighbours, which would bleed the
        "Sold Out" badge across in-stock cards.
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        sold_out_urls = set()
        for mark in soup.select(".product-mark.sold-out"):
            card = mark.find_parent("a", class_="product-list-item-link") or mark.find_parent(
                "a", href=lambda h: h and "/coffee/p/" in str(h)
            )
            if card is not None and card.get("href"):
                sold_out_urls.add(self._normalize_url(self.resolve_url(str(card["href"]))))
        logger.info(f"Found {len(sold_out_urls)} sold-out product(s) on {store_url}")

        product_urls = []
        for item in soup.select(".product-list-item-link, a[href*='/coffee/p/']"):
            if item.name != "a":
                continue
            url = self.resolve_url(item["href"])
            if self._normalize_url(url) in sold_out_urls:
                continue
            product_urls.append(url)

        product_urls = list(dict.fromkeys(product_urls))

        coffee_urls = [
            url
            for url in product_urls
            if self.is_coffee_product_url(url, required_path_patterns=["/coffee/p/"])
            and not any(ex in url.lower() for ex in self._get_excluded_url_patterns())
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
            translate_to_english=False,  # English store
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
        if "/coffee/p/" not in url:
            return soup

        # Swan Song's structured data lives in <head> meta tags. The og:description
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
            stock = "instock" if (v.get("stock") or {}).get("unlimited") else "unknown"
            line = f"- Size: {size} | Price: {price} {currency} | Stock: {stock}"
            lines.append(line)
        container.string = "\n".join(lines)
        return container

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Hardcode GBP as the store currency (Swan Song emits product:price:currency)."""
        bean.currency = "GBP"
        return bean

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup | Tag:
        """No extra pruning needed — meta tags already carried by fetch_page."""
        return soup
