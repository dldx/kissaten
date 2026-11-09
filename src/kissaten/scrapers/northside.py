"""Northside Coffee Roasters scraper implementation with AI-powered extraction.

Northside Coffee Roasters (www.northsidecoffee.co — note canonical ``.co``, not
``.co.uk``) is a micro-roastery & coffee shop in Morpeth, Northumberland.
The storefront was rebuilt on Wix headless with a fully custom, server-rendered
theme (no ``data-hook`` Wix store widgets). The whole-bean catalogue lives on
the ``/shop.html`` listing page (``/buy-coffee`` 301-redirects there). Product
cards are plain ``<a href="/product-page/<slug>.html">`` links inside
``<section id="coffee-range">``.

Product detail pages embed all useful coffee information inside
``<section id="product-detail" class="product-shell">`` plus a
``<script id="northside-seo" type="application/ld+json">`` Product schema
(name, description, image, sku). Prices/options load via JavaScript (the
static HTML shows "Enable JavaScript to check current options and shop
online"), so the AI extractor relies on the ld+json data plus the rendered
HTML text.

The ``/shop.html`` listing also carries a handful of non-coffee items sold
alongside the beans (Huskee cups, a camping mug, a cafiza machine-cleaning
powder, and a single-origin hot chocolate). Those are excluded via a
roaster-specific override of ``_get_excluded_url_patterns`` so only whole-bean
coffee reaches the AI extractor; curated samplers/taster packs (none currently
on the page) are deliberately NOT excluded and instead flow through to be
flagged ``is_tasting_kit``/``requires_review`` by the base class.
"""

import logging

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="northside",
    display_name="Northside Coffee Roasters",
    roaster_name="Northside Coffee Roasters",
    website="https://www.northsidecoffee.co",
    description="Micro-roastery & coffee shop in Morpheth, Northumberland (Wix storefront).",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class NorthsideScraper(BaseScraper):
    """Scraper for Northside Coffee Roasters (northsidecoffee.co) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Northside Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Northside Coffee Roasters",
            base_url="https://www.northsidecoffee.co",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

        # The Wix storefront exposes no og:price:currency meta tag, so the base
        # currency detection never fires and default_currency falls back to the
        # registry default. Northside prices in GBP (£); pin it up front so every
        # product page uses the correct currency without re-parsing.
        self.store_currency = "GBP"
        self._currency_detected = True

    def _get_excluded_url_patterns(self) -> list[str]:
        """Return base exclusions plus Northside-specific non-coffee patterns.

        The base exclusion set covers common equipment/merch tokens but not the
        drinkware/equipment sold alongside the beans on the single ``/buy-coffee``
        listing (Huskee cups, a camping mug, a cafiza machine-cleaning powder) or
        the single-origin hot chocolate drink. Adding these keeps only whole-bean
        coffee in the product set. Sampler/taster-pack tokens are intentionally
        NOT added here so any curated kits flow through to be flagged
        is_tasting_kit/requires_review instead of being dropped.
        """
        return super()._get_excluded_url_patterns() + [
            # Drinkware / equipment sold on the same /buy-coffee listing
            "huskee-cup",
            "camping-mug",
            "cafiza",
            "cleaning-powder",
            # Hot chocolate drink — not whole-bean coffee
            "hot-chocolate",
        ]

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape (the single /shop.html whole-bean listing).

        The storefront was rebuilt; the old ``/buy-coffee`` path 301-redirects
        to ``/shop.html``, which is the current canonical listing URL.

        Returns:
            List containing the coffee collection URL.
        """
        return ["https://www.northsidecoffee.co/shop.html"]

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page and narrow product detail pages to the product shell container.

        Product detail pages embed all useful content inside
        ``<section id="product-detail" class="product-shell">`` plus a
        ``<script id="northside-seo">`` ld+json Product block. Narrowing the
        soup to that container strips nav, footer, JSON blobs, and unrelated
        markup before the HTML is sent to the AI extractor, keeping token usage
        low. The listing page (``/shop.html``) is left untouched.

        Args:
            *args: Positional arguments forwarded to the base fetch_page.
            **kwargs: Keyword arguments forwarded to the base fetch_page.

        Returns:
            BeautifulSoup object (narrowed for product pages) or None if fetch failed.
        """
        url = kwargs.get("url")
        if not url and len(args) > 0:
            url = args[0]
        try:
            soup = await super().fetch_page(*args, **kwargs)
            # Only narrow product detail pages, leave the listing page untouched
            if "/product-page/" not in (url or ""):
                return soup
            if soup is None:
                return None
            product_el = soup.select("section#product-detail, section.product-shell")
            if len(product_el) == 1:
                logger.debug(f"Narrowed soup to section#product-detail for {url}")
                return product_el[0]
            logger.warning(f"Expected 1 section#product-detail for {url}, found {len(product_el)}")
            return soup
        except Exception as e:
            logger.error(f"Error fetching page {url}: {e}")
            return None

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        # The Wix storefront has no og:price:currency meta tag, so the base
        # currency detection never fires. Northside prices in GBP; force it.
        bean.currency = "GBP"
        return bean

    async def _scrape_new_products(self, product_urls: list[str], use_optimized_mode: bool = False) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction.

        Args:
            product_urls: List of URLs for new products
            use_optimized_mode: Whether to use optimized (visual) extraction mode

        Returns:
            List of newly scraped CoffeeBean objects
        """
        if not product_urls:
            return []

        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=False,
            use_optimized_mode=use_optimized_mode,
        )

    # Sold-out detection: text detection on the product card. When a product is
    # sold out, the card text contains "Sold out" / "Unavailable" / "Out of
    # stock" markers. We skip any card whose text contains those markers before
    # applying is_coffee_product_url filtering, so excluded products don't leak
    # past the stock check. The base-class exclusion patterns plus the
    # Northside-specific override drop non-bean items (cups, mugs, machine
    # cleaner, hot chocolate); tasting kits/samplers are deliberately NOT
    # excluded here and instead flow through to be flagged is_tasting_kit /
    # requires_review by the base class.
    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract coffee product URLs from the /shop.html listing, filtering sold-out items.

        The rebuilt storefront renders product cards as plain anchor tags inside
        ``<section id="coffee-range">``; there are no Wix ``data-hook`` store
        widgets anymore. Each card looks like::

            <section id="coffee-range">
              <a href="/product-page/<slug>.html"> ... </a>
              ...
            </section>

        Args:
            store_url: URL of the store/category page

        Returns:
            List of in-stock coffee product URLs
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        product_urls: list[str] = []
        seen: set[str] = set()

        # The coffee range section holds the bean listing; links point to
        # /product-page/<slug>.html product detail pages.
        range_section = soup.select_one("section#coffee-range") or soup
        for link in range_section.select('a[href*="/product-page/"]'):
            href = link.get("href")
            if not href or not isinstance(href, str):
                continue

            # Strip query string and fragment to get the canonical product URL
            full_url = self.resolve_url(href.split("?")[0].split("#")[0])

            # Skip sold-out products before URL-pattern filtering. Sold-out
            # cards render with an explicit "Sold out" / "Unavailable" badge in
            # the link text.
            item_text = link.get_text(" ", strip=True)
            if any(marker in item_text for marker in ("Unavailable", "Sold out", "Out of stock", "SOLD OUT")):
                logger.debug(f"Skipping sold-out product: {full_url}")
                continue

            # Apply standard coffee-product URL filtering (uses /product-page/ path
            # pattern plus the base + Northside-specific exclusion patterns).
            if not self.is_coffee_product_url(full_url, required_path_patterns=["/product-page/"]):
                continue

            if full_url not in seen:
                seen.add(full_url)
                product_urls.append(full_url)

        logger.info(f"Found {len(product_urls)} in-stock product URLs from {store_url}")
        return product_urls
