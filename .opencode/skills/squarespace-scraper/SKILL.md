---
name: squarespace-scraper
description: Generate a Kissaten scraper for a Squarespace-hosted coffee roaster site (e.g., Pala Kaffebrenneri, pala.no). Use when the user says "add a Squarespace scraper for <store>", "new Squarespace roaster <domain>", or supplies a Squarespace storefront URL.
license: Proprietary
compatibility: Python 3.10+, uv, network access to the target store, Playwright, optional GOOGLE_API_KEY for AI extraction
allowed-tools: Bash(curl:*) Bash(python:*) Bash(playwright:*) Read Write Edit Grep Glob
---

# Squarespace Scraper Generator

## When to Use
Use this skill when creating a Kissaten coffee bean scraper for a roaster hosted on Squarespace (e.g., `pala.no`, `coborncoffee.com`, `curveroasters.co.uk`).

Squarespace storefronts do not expose standard Shopify `products.json` endpoints. Instead, they use a structured pattern:
1. Product listing pages with path patterns like `/butikk/p/` or `/shop/p/`.
2. Clean `og:*` and `product:*` meta tags in the HTML `<head>`.
3. Embedded per-variant pricing and size data inside `<script data-name="static-context">` (`Static.SQUARESPACE_CONTEXT`).
4. Visual product/roast info captured via Playwright screenshots after dismissing cookie banners and stripping recommendation sections.

---

## Pattern Overview

### 1. Class Architecture
- Subclass `BaseScraper` directly.
- Initialize `CoffeeDataExtractor(api_key=api_key)`.
- Register via `@register_scraper(...)` with byte-identical `roaster_name` in both `@register_scraper` and `super().__init__`.
- Match `country` against `src/kissaten/database/roaster_location_codes.csv`.

### 2. Store Listing & Link Extraction (`_extract_product_urls_from_store`)
- Fetch store listing URL (e.g., `https://pala.no/butikk`).
- Extract product links matching `/p/` or `/shop/p/`.
- Perform card-level text checks for sold-out badges (e.g., `"utsolgt"` or `"sold out"`) on each product card before filtering URLs.
- Exclude shop-specific non-coffee items (subscriptions, courses, Hario/AeroPress hardware, filters, gift cards).

### 3. Meta-Only Soup + Static Context Variants (`fetch_page` & `_extract_variants`)
To optimize token usage while retaining 100% of structured product facts:
- In `fetch_page`, return a minimal soup containing only:
  - Meta tags: `og:title`, `og:description`, `product:price:amount`, `product:price:currency`, `product:availability`, `name="description"`.
  - Parsed variants text from `<script data-name="static-context">`.
- `_extract_variants(soup)` parses `Static.SQUARESPACE_CONTEXT = {...}` using regex:
  ```python
  match = re.search(r"Static\.SQUARESPACE_CONTEXT\s*=\s*(\{.*?\})\s*;\s*$", blob, re.DOTALL)
  ```
  And formats per-variant size, price, currency, and stock:
  ```
  Variants:
  - Size: 250g | Price: 248.00 NOK | Stock: instock
  - Size: 1kg | Price: 892.00 NOK | Stock: instock
  ```

### 4. Clean Playwright Screenshots (`take_screenshot`)
Override `take_screenshot` to ensure clean, unobscured visual analysis for Gemini:
- **Dismiss Cookie Banner**: Wait for and click `.sqs-cookie-banner-v2-accept` or `button.accept`.
- **Prune Related Products**: Remove DOM recommendation sections (`div.product-related-products, .related-products`) before capturing screenshot:
  ```python
  await page.evaluate("""() => {
      const els = document.querySelectorAll('div.product-related-products, .related-products');
      els.forEach(el => el.remove());
  }""")
  ```
- **Lazy-Load Trigger**: Scroll down to trigger image loading, then scroll back to top before `page.screenshot(full_page=True, type="png")`.

### 5. AI Extraction & Post-Processing
- In `_scrape_new_products`, delegate to `self.scrape_with_ai_extraction(...)`:
  - `use_optimized_mode=True` (sends page screenshot alongside meta-only HTML).
  - `translate_to_english=True` if non-English (e.g., Norwegian `pala.no`).
- In `postprocess_extracted_bean`, hardcode currency (e.g., `bean.currency = "NOK"`) as a final guard since Squarespace uses `product:price:currency` rather than `og:price:currency`.

---

## Canonical Reference Implementation

Reference implementation: `src/kissaten/scrapers/pala_kaffebrenneri.py`.

```python
"""Squarespace roaster scraper template."""

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
    name="example-squarespace",
    display_name="Example Roaster",
    roaster_name="Example Roaster",
    website="https://exampleroaster.no",
    description="Specialty coffee roaster on Squarespace.",
    requires_api_key=True,
    currency="NOK",
    country="Norway",
    status="available",
)
class ExampleSquarespaceScraper(BaseScraper):
    """Scraper for Squarespace coffee roasters."""

    def __init__(self, api_key: str | None = None):
        super().__init__(
            roaster_name="Example Roaster",
            base_url="https://exampleroaster.no",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        return ["https://exampleroaster.no/butikk"]

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        product_urls = []
        for item in soup.select(".ProductList-item, a[href*='/butikk/p/']"):
            card_text = " ".join(item.get_text(" ", strip=True).split()).lower()
            if "utsolgt" in card_text or "sold out" in card_text:
                continue
            if item.name == "a":
                product_urls.append(self.resolve_url(item["href"]))
            else:
                for a in item.find_all("a", href=True):
                    if "/butikk/p/" in a["href"]:
                        product_urls.append(self.resolve_url(a["href"]))

        product_urls = list(dict.fromkeys(product_urls))
        excluded = ["abonnement", "kurs", "filter", "hardware", "gift-card"]
        return [
            url for url in product_urls
            if self.is_coffee_product_url(url, required_path_patterns=["/butikk/p/"])
            and not any(ex in url.lower() for ex in excluded)
        ]

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        if not product_urls:
            return []

        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=False,
            use_optimized_mode=True,
            translate_to_english=True,
        )

    async def take_screenshot(self, url: str, full_page: bool = True) -> bytes | None:
        browser = await self._get_browser()
        page = await browser.new_page()

        try:
            signed_headers = self.get_signed_headers(url)
            await page.set_extra_http_headers({**self.headers, **signed_headers})
            response = await page.goto(url, timeout=self.timeout * 1000, wait_until="networkidle")

            if not response or not response.ok:
                raise Exception(f"Failed to load page: {response.status if response else 'No response'}")

            # Dismiss cookie banner
            try:
                accept_btn = await page.wait_for_selector(".sqs-cookie-banner-v2-accept, button.accept", timeout=3000)
                if accept_btn:
                    await accept_btn.click()
                    await page.wait_for_timeout(1000)
            except Exception as e:
                logger.debug(f"No cookie banner dismissed: {e}")

            # Remove related products
            try:
                await page.evaluate("""() => {
                    const els = document.querySelectorAll('div.product-related-products, .related-products');
                    els.forEach(el => el.remove());
                }""")
            except Exception as e:
                logger.debug(f"Could not remove related products: {e}")

            # Trigger scroll for lazy load
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1000)
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(500)

            return await page.screenshot(full_page=full_page, type="png")
        finally:
            await page.close()

    async def fetch_page(self, *args, **kwargs):
        soup = await super().fetch_page(*args, **kwargs)
        url = kwargs.get("url") or (args[0] if args else "")
        if "/butikk/p/" not in url:
            return soup

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
            lines.append(f"- Size: {size} | Price: {price} {currency} | Stock: {stock}")

        container.string = "\n".join(lines)
        return container

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        bean.currency = "NOK"
        return bean
```

---

## Registry Integration
Remember to update `src/kissaten/scrapers/__init__.py`:
1. Add `from .<module_name> import <ClassName>` in alphabetical order.
2. Add `<ClassName>` to `__all__` in alphabetical order.

Validate with:
```bash
uv run python -c "from kissaten.scrapers.registry import get_registry; print(get_registry().get_scraper_info('<scraper-name>'))"
uv run ruff check src/kissaten/scrapers/<module_name>.py
```
