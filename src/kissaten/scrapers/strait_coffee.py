"""Strait Coffee Roasters scraper implementation with AI-powered extraction."""

import logging
from pathlib import Path

from bs4 import BeautifulSoup, Tag
from playwright.async_api import Page

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="strait-coffee",
    display_name="Strait Coffee Roasters",
    roaster_name="Strait Coffee Roasters",
    website="https://www.thestraitcoffee.com",
    description="Specialty coffee roaster based in San Jose, California roasting on a clean-air "
    "electric fluid-bed roaster, focused on ultra-premium single-origin coffees",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="available",
)
class StraitCoffeeScraper(BaseScraper):
    """Scraper for Strait Coffee Roasters (thestraitcoffee.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Strait Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Strait Coffee Roasters",
            base_url="https://www.thestraitcoffee.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        The /coffee page lists currently available beans. The /coffee-archive
        page lists historical (sold-out) beans which we scrape on the first run
        to capture the full back-catalogue.

        Returns:
            List containing the coffee collection URLs
        """
        return [
            "https://www.thestraitcoffee.com/coffee",
            "https://www.thestraitcoffee.com/coffee-archive",
        ]

    async def _fetch_with_playwright(self, url: str) -> str:
        """Fetch page with Playwright, dismissing the Cookiebot consent banner and
        auto-scrolling to load lazily-rendered product cards.
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
                    necessary_button = page.locator('button:has-text("Use necessary cookies only")')
                    if await necessary_button.count() > 0:
                        await necessary_button.first.click()
                        logger.info("Clicked 'Use necessary cookies only' button")
            except Exception as e:
                logger.debug(f"Cookie banner handling: {e}")

            # Wait for appropriate content depending on page type
            if "/product/" in url:
                try:
                    await page.wait_for_selector("div.product-detail-page", timeout=15000)
                    logger.info("Product detail page loaded")
                except Exception:
                    await page.wait_for_timeout(3000)
                    logger.warning(f"Timed out waiting for product detail page on {url}")
            else:
                # Wait for product cards to appear, then auto-scroll to load lazy content on store pages.
                try:
                    await page.wait_for_selector("div.product-group", timeout=15000)
                    logger.info("Product cards appeared on page")
                except Exception:
                    await page.wait_for_timeout(3000)
                    logger.warning(f"Timed out waiting for product cards on {url}")

                await self._auto_scroll(page)

            content = await page.content()
            return content

        finally:
            await page.close()

    async def _auto_scroll(self, page: Page) -> int:
        """Scroll to the bottom of the page until no new product cards load."""
        max_scrolls = 60
        scroll_delay = 900  # ms between scrolls
        previous_count = 0
        stable_rounds = 0
        scroll_attempts = 0

        while scroll_attempts < max_scrolls:
            await page.mouse.wheel(0, 5000)
            await page.wait_for_timeout(scroll_delay)

            current_count = await page.evaluate("document.querySelectorAll('div.product-group').length")

            if current_count == previous_count:
                stable_rounds += 1
                if stable_rounds >= 2:
                    break
            else:
                stable_rounds = 0

            previous_count = current_count
            scroll_attempts += 1

        logger.debug(f"Auto-scroll finished after {scroll_attempts} attempts ({previous_count} cards)")
        return scroll_attempts

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page and narrow product detail pages to the product container.

        Automatically appends the query string `?cs=true&cst=custom` to product detail
        pages because it is required by Square Online to render the product page instead of
        redirecting to the cart.
        """
        try:
            # Check the URL being fetched
            url = kwargs.get("url")
            if not url and len(args) > 0:
                url = args[0]

            if url and "/product/" in url and "cs=true" not in url:
                if "?" in url:
                    url += "&cs=true&cst=custom"
                else:
                    url += "?cs=true&cst=custom"
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
                    return product_el[0]
                logger.warning(f"No product-detail-page section found for URL {url}")

            return soup
        except Exception as e:
            logger.error(f"Error fetching page: {e}")
            return None

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from a store (collection) page.

        URLs are cleaned to strip query parameters.
        """
        soup = await self.fetch_page(store_url, use_playwright=True)
        if not soup:
            logger.error(f"Failed to fetch page: {store_url}")
            return []

        is_archive = "coffee-archive" in store_url
        sold_out_markers = ("Out of stock", "Sold out", "SOLD OUT", "Unavailable")

        product_urls: list[str] = []
        cards = soup.select("div.product-group")
        logger.info(f"Found {len(cards)} product cards on {store_url}")

        for card in cards:
            link = card.select_one('a[href*="/product/"]')
            if not link or not hasattr(link, "get"):
                continue
            href = link.get("href")
            if not href or not isinstance(href, str):
                continue

            if not is_archive:
                card_text = card.get_text(" ", strip=True)
                if any(marker in card_text for marker in sold_out_markers):
                    logger.debug(f"Skipping sold-out product card: {href}")
                    continue

            full_url = self.resolve_url(href)
            # Strip query string from URL before checking/adding to database
            if "?" in full_url:
                full_url = full_url.split("?")[0]

            if self.is_coffee_product_url(full_url, required_path_patterns=["/product/"]):
                product_urls.append(full_url)

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_urls: list[str] = []
        for url in product_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        if is_archive:
            # Drop already-scraped archive URLs so they fall through to out-of-stock marking
            self._load_existing_beans_from_all_sessions(Path("data"))
            new_archive_urls = [url for url in unique_urls if not self._is_bean_already_scraped_anywhere(url)]
            skipped = len(unique_urls) - len(new_archive_urls)
            logger.info(
                f"Archive: returning {len(new_archive_urls)} new URLs; "
                f"skipping {skipped} already-scraped beans (will be marked out of stock)"
            )
            return new_archive_urls

        logger.info(f"Found {len(unique_urls)} product URLs from {store_url} (current, sold-out filtered)")
        return unique_urls

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction."""
        if not product_urls:
            return []

        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=True,
            use_optimized_mode=True,
        )

    async def take_screenshot(self, url: str, full_page: bool = True) -> bytes | None:
        """Take a screenshot focused on the product-detail-page element."""
        # Ensure url has Square Online query params on product page if needed
        if "/product/" in url and "cs=true" not in url:
            if "?" in url:
                url += "&cs=true&cst=custom"
            else:
                url += "?cs=true&cst=custom"

        browser = await self._get_browser()
        page: Page = await browser.new_page()

        try:
            # Set viewport for consistent screenshots
            await page.set_viewport_size({"width": 1200, "height": 800})

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
                    necessary_button = page.locator('button:has-text("Use necessary cookies only")')
                    if await necessary_button.count() > 0:
                        await necessary_button.first.click()
                        logger.info("Clicked 'Use necessary cookies only' button")
            except Exception as e:
                logger.debug(f"Cookie banner handling in take_screenshot: {e}")

            # Wait for the product-detail-page element to be present
            try:
                await page.wait_for_selector("div.product-detail-page", timeout=15000)

                # Take a screenshot of just the product-detail-page element
                element = page.locator("div.product-detail-page")
                screenshot_bytes = await element.screenshot(type="png")
                logger.info(f"Successfully took product div screenshot of: {url}")
                return screenshot_bytes

            except Exception as e:
                logger.warning(f"Could not find div.product-detail-page on {url}, taking full page screenshot: {e}")
                # Fallback to full page screenshot
                screenshot_bytes = await page.screenshot(type="png", full_page=True)
                return screenshot_bytes

        except Exception as e:
            logger.error(f"Failed to take screenshot of {url}: {e}")
            return None

        finally:
            await page.close()

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Force USD currency and clean query strings from the URL."""
        bean.currency = "USD"
        if bean.url and "?" in str(bean.url):
            # Clean URL to match database schema conventions without query parameters
            from urllib.parse import unquote, urlsplit, urlunsplit

            decoded = unquote(str(bean.url))
            parts = urlsplit(decoded)
            bean.url = urlunsplit(parts._replace(query=""))

        return super().postprocess_extracted_bean(bean)
