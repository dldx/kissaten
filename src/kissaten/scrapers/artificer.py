"""Artificer scraper implementation with AI-powered extraction (Square Online)."""

import logging

from bs4 import BeautifulSoup, Tag
from playwright.async_api import Page

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="artificer",
    display_name="Artificer",
    roaster_name="Artificer",
    website="https://artificercoffee.com/",
    description="Specialty coffee bar & roastery based in Surry Hills, Sydney, Australia, "
    "focused on the correlation between selection, roasting and brewing.",
    requires_api_key=True,
    currency="AUD",
    country="Australia",
    status="available",
)
class ArtificerScraper(BaseScraper):
    """Scraper for Artificer (artificercoffee.square.site) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Artificer scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Artificer",
            base_url="https://artificercoffee.square.site",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor (gracefully degrades to None when no API key
        # is configured, matching the base class, so connectivity-only smoke
        # tests work without a key).
        self.ai_extractor = None
        try:
            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
        except ValueError:
            logger.warning("Google API key not configured. AI extraction will not be available.")

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Artificer is a JS-rendered Square Online store whose product cards render
        as clickable buttons without anchor hrefs, so the ordinary listing pages
        expose no discoverable ``/product/`` links. Square Online publishes a
        static ``sitemap.xml`` that lists every product URL, which we use as the
        discovery source instead.

        Returns:
            List containing the sitemap URL.
        """
        return ["https://artificercoffee.square.site/sitemap.xml"]

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
        )

    async def _fetch_with_playwright(self, url: str) -> str:
        """Fetch page with Playwright, waiting for Square Online product content.

        Square Online renders the product detail (name, price, description) lazily
        inside ``div.product-detail-page`` after a short settle period. We wait for
        that container so the AI extractor receives the actual product content.
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
        render the product instead of redirecting to the cart. We append that query
        string and, for product detail URLs, narrow the soup to
        ``div.product-detail-page`` before passing it to the AI extractor to cut
        token noise.

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

    # Non-coffee URL slugs to exclude (equipment/merch shown in the sitemap).
    _excluded_url_slugs = [
        "aeropress-maker",
        "cap-v2-0",
        "drip-bag",
        "gesha-pour-over",
        "logo-market-tote",
        "origami-dripper-m",
        "socks-attaquer",
    ]

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from the sitemap.xml.

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
            # Exclude non-coffee equipment/merch slugged in the sitemap
            url_lower = url.lower()
            if any(slug in url_lower for slug in self._excluded_url_slugs):
                logger.debug(f"Excluding non-coffee product URL: {url}")
                continue
            product_urls.append(url)

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_urls: list[str] = []
        for url in product_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        logger.info(f"Found {len(unique_urls)} coffee product URLs from sitemap")
        return unique_urls
