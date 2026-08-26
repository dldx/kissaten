"""Sunday Coffee Roasters scraper implementation with AI extraction.

Sunday Coffee Roasters (sundaycoffee.co.uk) is a Squarespace-hosted
storefront (roastery in Southbourne/Emsworth, Hampshire; trading as
"Sunday Roastery Ltd"). Products live at ``/coffees/...`` and carry the
standard Squarespace product-page meta tags (``og:title``, ``og:description``,
``product:price:*``, ``product:availability``) plus a ``static-context`` JSON
blob with per-variant size/price/currency/stock.

Discovery crawls the ``/coffees`` listing and keeps whole-bean coffee products
only — excluding merchandise (mugs, tote bags, apparel). Curated samplers
(e.g. the "Coffee Taster Box v3" and the "First Batch and Friends" box) are
retained and flagged for review rather than dropped.
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
    name="sunday-coffee",
    display_name="Sunday Coffee Roasters",
    roaster_name="Sunday Coffee Roasters",
    website="https://sundaycoffee.co.uk",
    description=(
        "Specialty coffee roaster based in Southbourne/Emsworth, Hampshire, "
        "UK (trading as Sunday Roastery Ltd), offering seasonal single origins, "
        "blends, and a rotating coffee taster box roasted fresh."
    ),
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class SundayCoffeeScraper(BaseScraper):
    """Scraper for Sunday Coffee Roasters (sundaycoffee.co.uk) — a Squarespace storefront.

    We leverage the Squarespace product-page meta tags (og:title, og:description,
    product:price:*, product:availability) and static-context variants JSON
    alongside page screenshots to extract CoffeeBean models.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Sunday Coffee scraper."""
        super().__init__(
            roaster_name="Sunday Coffee Roasters",
            base_url="https://sundaycoffee.co.uk",
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
        """Return the Squarespace coffees (/coffees) listing URL."""
        return ["https://sundaycoffee.co.uk/coffees"]

    def _get_excluded_url_patterns(self) -> list[str]:
        """Add Sunday-specific non-coffee exclusions on top of the base set.

        The base list already drops generic equipment/merch/service patterns
        (grinder, v60, subscription, gift-card, shirt, tote, ...). Sunday only
        needs a few merchandise additions: mugs and gift bundles.
        """
        return super()._get_excluded_url_patterns() + [
            "mug",
            "tote-bag",
            "gift-voucher",
            "merch",
        ]

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract coffee product URLs from the Squarespace /coffees listing page.

        Squarespace renders each product card with a ``.ProductList-item`` class
        and a ``/coffees/`` link. We keep only coffee product URLs that are not
        excluded merchandise. Sold-out cards are retained so their beans remain
        in the catalogue (marked out of stock by the AI/product meta) rather than
        disappearing.
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        product_urls = []
        for item in soup.select(".ProductList-item, a[href*='/coffees/']"):
            if item.name == "a":
                product_urls.append(self.resolve_url(item["href"]))
            else:
                for a in item.find_all("a", href=True):
                    if "/coffees/" in a["href"]:
                        product_urls.append(self.resolve_url(a["href"]))

        product_urls = list(dict.fromkeys(product_urls))

        coffee_urls = [
            url
            for url in product_urls
            if self.is_coffee_product_url(url, required_path_patterns=["/coffees/"])
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
        if "/coffees/" not in url:
            return soup

        # Sunday's structured data lives in <head> meta tags. The og:description
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

    def postprocess_review_flags(self, bean, url: str):
        """Flag Sunday's curated sampler boxes as tasting kits.

        The ``tasterbox`` handle is already caught by the base kit URL patterns
        ("taster"), but the "First Batch and Friends" box carries no kit token in
        its handle/name, so we force ``is_tasting_kit`` here so it lands in the
        admin review queue instead of public search.
        """
        name = getattr(bean, "name", "") or ""
        name_lower = str(name).lower()
        if "taster box" in name_lower or "first batch" in name_lower:
            bean.is_tasting_kit = True
        return bean

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Hardcode GBP as the store currency (Sunday emits product:price:currency)."""
        bean.currency = "GBP"
        return bean

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup | Tag:
        """No extra pruning needed — meta tags already carried by fetch_page."""
        return soup
