"""ONI Coffee Roasters scraper implementation with AI-powered extraction (Next.js)."""

import logging

from playwright.async_api import Page

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="oni-coffee-roasters",
    display_name="ONI Coffee Roasters",
    roaster_name="ONI Coffee Roasters",
    website="https://www.onicoffeeroasters.ie",
    description="ONI Roasters brings you limited-batch coffees, meticulously profiled and roasted in Dublin. For those who brew with intent.",
    requires_api_key=True,
    currency="EUR",
    country="Republic of Ireland",
    status="available",
)
class OniCoffeeRoastersScraper(BaseScraper):
    """Scraper for ONI Coffee Roasters (onicoffeeroasters.ie) with AI-powered extraction.

    ONI's storefront is a Next.js App Router application. The shop listing page
    is server-side rendered (product links visible in initial HTML), but
    individual product detail pages only render skeleton loading states in SSR
    — the actual content is embedded in RSC flight data and rendered client-side
    via JavaScript. We therefore use httpx for the listing page and Playwright
    for product detail pages.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize ONI Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="ONI Coffee Roasters",
            base_url="https://www.onicoffeeroasters.ie",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the coffee beans category URL.
        """
        return ["https://www.onicoffeeroasters.ie/shop?category=COFFEE_BEANS"]

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction with Playwright.

        Product detail pages are client-rendered (SSR only produces skeleton
        loaders), so Playwright is required to execute the RSC flight data
        and render the actual product content.

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
            use_playwright=True,
            use_optimized_mode=False,
            translate_to_english=False,
        )

    async def _fetch_with_playwright(self, url: str) -> str:
        """Fetch page content using Playwright, waiting for RSC content to render.

        Next.js App Router pages ship with skeleton loaders (``.animate-pulse``)
        in the SSR HTML. The actual product data is embedded in RSC flight data
        (``self.__next_f.push`` calls) and rendered client-side. We navigate to
        the page, wait for an ``h1`` element to appear (which only exists after
        React hydrates and replaces the skeleton loaders), then return the
        fully rendered HTML.

        Args:
            url: URL to fetch

        Returns:
            Full rendered HTML content as string

        Raises:
            Exception: If fetch fails
        """
        browser = await self._get_browser()
        page: Page = await browser.new_page()

        try:
            await page.set_extra_http_headers(self.headers)

            response = await page.goto(url, timeout=self.timeout * 1000, wait_until="domcontentloaded")

            if not response or not response.ok:
                raise Exception(f"Failed to load page: {response.status if response else 'No response'}")

            # Wait for React hydration: the SSR HTML has only skeleton loaders
            # (.animate-pulse) with no h1. When h1 appears, the product content
            # has been rendered from the RSC flight data.
            try:
                await page.wait_for_selector("h1", timeout=15000)
                logger.debug(f"Product content rendered (h1 found) for {url}")
            except Exception:
                logger.warning(f"Timed out waiting for h1 on {url}; proceeding with current content")

            # Small buffer for any remaining content (images, variant selectors)
            await page.wait_for_timeout(1000)

            content = await page.content()
            return content

        finally:
            await page.close()

    # Sold-out detection: text detection on the <a> tag itself.
    # ONI's listing page renders each product card as an <a> tag whose text
    # contains the full card content (name, origin, price, tasting notes).
    # Sold-out products have "Out of stock" prepended to the link text. We
    # check the <a> element's text directly — no parent/sibling traversal
    # needed — before applying is_coffee_product_url filtering.
    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from the Next.js SSR shop listing.

        The listing page is server-side rendered: product links appear as
        ``<a href="/shop/<cuid>">`` tags inside the product grid. Each ``<a>``
        tag wraps the full card content (name, origin, price, tasting notes,
        and "Out of stock" badge if applicable).

        Because product URLs use ``/shop/<cuid>`` (no ``/product/`` or
        ``/products/`` segment), ``is_coffee_product_url``'s default path
        patterns would reject every URL; we pass ``required_path_patterns``
        explicitly to accept the ``/shop/`` prefix.

        Args:
            store_url: URL of the shop listing page

        Returns:
            List of in-stock product URLs
        """
        soup = await self.fetch_page(store_url, use_playwright=False)
        if not soup:
            return []

        product_urls: list[str] = []
        seen: set[str] = set()

        for link in soup.select('a[href^="/shop/"]'):
            href = link.get("href")
            if not href or not isinstance(href, str):
                continue
            # Skip the listing page itself (href="/shop" without a cuid)
            if href.rstrip("/") == "/shop":
                continue

            full_url = self.resolve_url(href.split("?")[0].split("#")[0])

            # Skip sold-out products (text detection on the <a> element itself)
            link_text = link.get_text(" ", strip=True)
            if "Out of stock" in link_text or "Sold out" in link_text:
                logger.debug(f"Skipping sold-out product: {full_url}")
                continue

            # Skip test products (ONI has a "Test Roast - Filter" product that
            # uses a cuid URL with no human-readable slug to filter on)
            if "test roast" in link_text.lower():
                logger.debug(f"Skipping test product: {full_url}")
                continue

            if not self.is_coffee_product_url(full_url, required_path_patterns=["/shop/"]):
                continue

            if full_url not in seen:
                seen.add(full_url)
                product_urls.append(full_url)

        logger.info(f"Found {len(product_urls)} in-stock product URLs from {store_url}")
        return product_urls

    def _get_excluded_product_name_categories(self) -> list[str]:
        """Add ONI-specific exclusions to the base list.

        ONI has a "Test Roast - Filter" product whose URL is a cuid with no
        human-readable slug. We exclude it here so it's also filtered out at
        the AI extraction stage (base.py calls is_coffee_product_name on
        bean.name after extraction) as defense-in-depth.

        Returns:
            List of excluded product name keywords
        """
        return super()._get_excluded_product_name_categories() + ["test roast"]

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Force EUR currency for all beans.

        ONI's Next.js pages have no ``og:price:currency`` meta tag or Shopify
        currency object, so the base class currency detection cannot auto-detect
        the currency. We explicitly set it to EUR (Republic of Ireland).

        Args:
            bean: Extracted CoffeeBean object

        Returns:
            CoffeeBean with currency set to EUR
        """
        bean.currency = "EUR"
        return bean
