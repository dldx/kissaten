"""LiB's Market scraper implementation with AI-powered extraction (Square Online)."""

import logging

from bs4 import BeautifulSoup, Tag
from playwright.async_api import Page

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="libs-market",
    display_name="LiB's Market",
    roaster_name="LiB's Market",
    website="https://www.libsmarket.com",
    description=(
        "LiB's Market is a family-owned specialty coffee roastery and cafe in "
        "Salem, Ohio, roasting in-house on a Diedrich IR-3 under its Full City "
        "Roastery brand."
    ),
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class LibsMarketScraper(BaseScraper):
    """Scraper for LiB's Market (libsmarket.com) — a Square Online storefront.

    Square Online (Weebly) renders the store entirely via JS: the listing pages
    expose no ``/product/`` anchors and the static HTML is just a ``<div id="app">``
    shell. Discovery therefore uses the static ``sitemap.xml`` (which lists every
    product URL), and product detail pages are fetched with Playwright. The site is
    a full cafe menu, so slug filtering keeps only roasted-bean products.
    """

    # Non-coffee URL slug substrings (cafe menu items, drinks, merch, packs).
    # The sitemap lists the whole cafe menu (bagels, flatbreads, lattes, teas,
    # merch, fundraiser packs), so require bean-ish slugs and drop the rest.
    _required_slug_terms = ["coffee", "blend", "fermentation"]
    _excluded_url_slugs = [
        "10th-anniversary-candle",  # candle trio (coffee-run candle)
        "libs-coffee-compost",  # coffee-ground compost, not beans
        "wholesale",  # wholesale bags are B2B duplicates
        "subscription",  # monthly coffee subscription
        "iced-coffee",  # cafe drink
        "drip-coffee",  # cafe drink
        "cold-brew",  # cafe drink / bottled cold brew
        "live-tasting",  # Fermentation Project live tasting event ticket
        "club-pack",
        "supporter-pack",
        "starter-pack",
        "tea-pack",
    ]

    def __init__(self, api_key: str | None = None):
        """Initialize LiB's Market scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="LiB's Market",
            base_url="https://www.libsmarket.com",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = None
        try:
            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
        except ValueError:
            logger.warning("Google API key not configured. AI extraction will not be available.")

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Square Online product cards render as JS-clickable elements without
        anchor hrefs, so the listing pages expose no ``/product/`` links. The
        static ``sitemap.xml`` lists every product URL and is used as the
        discovery source instead.

        Returns:
            List containing the sitemap URL.
        """
        return ["https://www.libsmarket.com/sitemap.xml"]

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction.

        Args:
            product_urls: List of URLs for new products

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
            use_playwright=True,  # Square Online renders product pages via JS
            use_optimized_mode=False,
            translate_to_english=False,
        )

    async def _fetch_with_playwright(self, url: str) -> str:
        """Fetch page with Playwright, waiting for Square Online product content.

        Square Online renders the product detail (name, price, description)
        lazily inside ``div.product-detail-page`` after a short settle period.

        Args:
            url: URL of the page to fetch

        Returns:
            Rendered page HTML as a string
        """
        browser = await self._get_browser()
        page: Page = await browser.new_page()

        try:
            await page.set_extra_http_headers(
                {
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                }
            )

            await page.goto(url, timeout=self.timeout * 1000, wait_until="domcontentloaded")

            # Wait for product detail to render, then give it a moment to settle.
            try:
                await page.wait_for_selector("div.product-detail-page", timeout=15000)
                await page.wait_for_timeout(1500)
                logger.info("Product detail page rendered")
            except Exception:
                await page.wait_for_timeout(4000)
                logger.warning(f"Timed out waiting for product detail on {url}")

            content = await page.content()
            return content

        finally:
            await page.close()

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page, adding Square Online detail params and narrowing product pages.

        Square Online requires ``?cs=true&cst=custom`` on product detail pages to
        render the product instead of redirecting to the cart. Product detail
        soups are narrowed to ``div.product-detail-page`` to cut token noise.

        Args:
            *args: Positional arguments forwarded to the base fetch_page.
            **kwargs: Keyword arguments forwarded to the base fetch_page.

        Returns:
            BeautifulSoup object (narrowed for product pages) or None if fetch failed.
        """
        try:
            url = kwargs.get("url")
            if not url and len(args) > 0:
                url = args[0]

            # Append the Square Online detail rendering query params.
            if url and "/product/" in url:
                if "cs=true" not in url:
                    separator = "&" if "?" in url else "?"
                    url = f"{url}{separator}cs=true&cst=custom"
                    if "url" in kwargs:
                        kwargs["url"] = url
                    elif len(args) > 0:
                        args = (url,) + args[1:]

            soup = await super().fetch_page(*args, **kwargs)
            if not soup:
                return None

            if url and "/product/" in url:
                product_el = soup.select("div.product-detail-page")
                if len(product_el) == 1:
                    logger.debug(f"Narrowed soup to div.product-detail-page for {url}")
                    return product_el[0]
                logger.warning(f"Expected 1 div.product-detail-page for {url}, found {len(product_el)}")

            return soup
        except Exception as e:
            logger.error(f"Error fetching page: {e}")
            return None

    # Sold-out detection: no listing-level stock signal exists. Square Online
    # renders the "Coffee & Retail" listing via JS (no anchors, no sold-out
    # badges in the static HTML), and the sitemap carries no availability data,
    # so checklist steps 1-3 cannot run at discovery time. Sold-out state is
    # captured on the rendered detail page instead: the AI extractor reads the
    # "Sold out" badge, and a fully de-listed product disappears from the
    # sitemap and is then reported out of stock by create_diffjson_stock_updates.
    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract coffee product URLs from the sitemap.xml.

        Args:
            store_url: URL of the sitemap page

        Returns:
            List of coffee product URLs
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
            # Only product detail URLs
            if not self.is_coffee_product_url(url, required_path_patterns=["/product/"]):
                continue

            # Slugs sit between /product/ and the trailing Square product id
            # (e.g. /product/12-oz-lib-s-fresh-premium-coffee/673).
            path = url.split("?")[0].split("#")[0]
            slug = path.split("/product/")[-1].rstrip("/").lower()

            # Keep only roasted-bean-ish slugs (the sitemap lists the whole
            # cafe menu: bagels, flatbreads, lattes, teas, merch, packs).
            if not any(term in slug for term in self._required_slug_terms):
                logger.debug(f"Skipping non-bean slug: {url}")
                continue

            # Drop the remaining drinks/merch/pack slugs.
            if any(excluded in slug for excluded in self._excluded_url_slugs):
                logger.debug(f"Excluding non-coffee product URL: {url}")
                continue

            product_urls.append(url.split("?")[0])

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_urls: list[str] = []
        for url in product_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        logger.info(f"Found {len(unique_urls)} coffee product URLs from sitemap")
        return unique_urls

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Pin USD as the store currency (Squarespace-style geo pricing guard)."""
        bean.currency = "USD"
        return bean
