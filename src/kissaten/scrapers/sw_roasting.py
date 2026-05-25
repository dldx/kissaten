"""S&W Roasting scraper implementation with AI-powered extraction."""

import logging

from bs4 import BeautifulSoup, Tag
from playwright.async_api import Page

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="sw-roasting",
    display_name="S&W Roasting",
    roaster_name="S&W Roasting",
    website="https://www.swroasting.coffee",
    description="Specialty coffee roaster offering single origins, blends, and roaster selections",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="available",
)
class SWRoastingScraper(BaseScraper):
    """Scraper for S&W Roasting (swroasting.coffee) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize S&W Roasting scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="S&W Roasting",
            base_url="https://www.swroasting.coffee",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the coffee collection URLs
        """
        return [
            "https://www.swroasting.coffee/shop/single-origin-coffees-lighter-roasts/2?page=1&limit=30&sort_by=category_order&sort_order=asc",
            "https://www.swroasting.coffee/shop/roasters-select/5?page=1&limit=30&sort_by=category_order&sort_order=asc",
            "https://www.swroasting.coffee/shop/blends-and-medium-roasts/3?page=1&limit=30&sort_by=category_order&sort_order=asc",
        ]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from S&W Roasting using AI extraction.

        Returns:
            List of CoffeeBean objects
        """
        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=self._extract_product_urls_from_store,
            ai_extractor=self.ai_extractor,
            use_playwright=True,  # May need JS for dynamic content
        )

    async def _fetch_with_playwright(self, url: str) -> str:
        """Fetch page with Playwright, dismissing the Cookiebot consent banner.

        S&W Roasting uses Square Online with Cookiebot, which blocks content
        rendering until cookies are accepted. The site also blocks bot User-Agents.
        """
        browser = await self._get_browser()
        page: Page = await browser.new_page()

        try:
            # Use a real browser user agent - S&W blocks bot UAs with 500 errors
            await page.set_extra_http_headers(
                {
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                }
            )

            await page.goto(url, timeout=self.timeout * 1000, wait_until="networkidle")

            # Dismiss the Cookiebot consent banner if present
            try:
                deny_button = page.locator(
                    'button#CybotCookiebotDialogBodyButtonDecline, button[id*="CookiebotDialog"][id*="Decline"]'
                )
                if await deny_button.count() > 0:
                    await deny_button.first.click()
                    logger.info("Dismissed Cookiebot consent banner")
                else:
                    # Try the "Use necessary cookies only" button
                    necessary_button = page.locator('button:has-text("Use necessary cookies only")')
                    if await necessary_button.count() > 0:
                        await necessary_button.first.click()
                        logger.info("Clicked 'Use necessary cookies only' button")
            except Exception as e:
                logger.debug(f"Cookie banner handling: {e}")

            # Wait for product content to load after cookie dismissal
            try:
                await page.wait_for_selector('a[href*="/product/"]', timeout=15000)
                logger.info("Product links appeared on page")
            except Exception:
                await page.wait_for_timeout(3000)
                logger.warning(f"Timed out waiting for product links on {url}")
                title = await page.title()
                logger.info(f"Page title after cookie handling: {title}")

            content = await page.content()
            return content

        finally:
            await page.close()

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page and return its BeautifulSoup object.

        Args:
            url: URL of the page to fetch
            use_playwright: Whether to use Playwright for fetching

        Returns:
            BeautifulSoup object of the page, or None if fetch failed
        """
        try:
            soup = await super().fetch_page(*args, **kwargs)
            url = kwargs.get("url")
            if not url and len(args) > 0:
                url = args[0]
            if "/product/" not in (url or ""):
                return soup  # Only modify product pages
            # Find product info section
            product_el = soup.select("div.product-detail-page")
            if len(product_el) == 1:
                return product_el[0]
            logger.warning(f"No product section found for URL {url}")
            return soup
        except Exception as e:
            logger.error(f"Error fetching page {url}: {e}")
            return None

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from store page.

        Args:
            store_url: URL of the store page

        Returns:
            List of product URLs
        """
        soup = await self.fetch_page(store_url, use_playwright=True)
        if not soup:
            logger.error(f"Failed to fetch page: {store_url}")
            return []

        # Log for debugging
        product_links = soup.select('a[href*="/product/"]')
        logger.info(f"Found {len(product_links)} raw product links on {store_url}")

        # Get all product URLs using the base class method
        product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/product/"],
            selectors=[
                'a[href*="/product/"]',
            ],
        )

        # Filter out excluded products
        excluded_products = [
            "cold-brew",  # Cold brew products
            "sample",  # Sample products
            "cascara",  # Tea
            "gift-card",  # Gift cards
            "thank-the-fellas",
        ]

        filtered_urls = []
        for url in product_urls:
            # Check if any excluded product identifier is in the URL
            if not any(excluded in url.lower() for excluded in excluded_products):
                filtered_urls.append(url.split("?")[0])  # Remove query parameters

        return list(set(filtered_urls))

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        bean.currency = "USD"
        return super().postprocess_extracted_bean(bean)
