"""Flames Coffee scraper implementation with AI-powered extraction."""

import asyncio
import logging

from bs4 import BeautifulSoup, Tag
from playwright.async_api import Page

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="flames-coffee",
    display_name="Flames Coffee",
    roaster_name="Flames Coffee",
    website="https://flames.com.ua",
    description="Speciality coffee roaster based in Ukraine.",
    requires_api_key=True,
    currency="UAH",
    country="Ukraine",
    status="available",
)
class FlamesCoffeeScraper(BaseScraper):
    """Scraper for Flames Coffee (flamescoffee.com.ua) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Flames Coffee scraper.
        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Flames Coffee",
            base_url="https://flames.com.ua",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the coffee collection URL
        """
        return ["https://flames.com.ua/coffee-filter/filter/fasovka=1,2,5,8;page=all/",
                "https://flames.com.ua/coffee-espresso/filter/fasovka=1,2,5,8;page=all/",
                "https://flames.com.ua/infuse-coffee/filter/fasovka=1,2,5,8;page=all/"
                ]  # Collection page with all coffee beans


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
            use_playwright=True,
            translate_to_english=True,
        )


    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        bean.currency = "UAH"
        return bean

    async def _fetch_with_playwright(self, url: str) -> str:
        """Fetch page content using Playwright, handling proof-of-work challenge.

        The site uses a JavaScript proof-of-work challenge. This method:
        1. Loads the page and waits for the challenge to be solved (page reloads)
        2. Waits for the challenge_passed cookie to be set
        3. Returns the full page HTML with all products

        Args:
            url: URL to fetch

        Returns:
            Full HTML page content as string with all products

        Raises:
            Exception: If fetch fails
        """
        browser = await self._get_browser()
        page: Page = await browser.new_page()

        try:
            # Set headers
            await page.set_extra_http_headers(self.headers)

            # Navigate to the page - this will trigger the challenge
            response = await page.goto(url, timeout=self.timeout * 1000, wait_until="domcontentloaded")

            if not response or not response.ok:
                raise Exception(f"Failed to load page: {response.status if response else 'No response'}")

            # Wait for challenge to be solved
            # The challenge script solves the proof-of-work, sets challenge_passed cookie, then reloads
            # We need to wait for the cookie to appear and then for the page reload
            max_wait_time = 30  # Maximum seconds to wait for challenge
            wait_interval = 0.5  # Check every 500ms
            waited = 0
            challenge_solved = False

            # Wait for challenge_passed cookie to appear
            while waited < max_wait_time:
                cookies = await page.context.cookies()
                challenge_passed = any(cookie.get("name") == "challenge_passed" for cookie in cookies)

                if challenge_passed:
                    logger.debug(f"Challenge solved, cookie found after {waited}s")
                    # The challenge script will reload the page, wait for it
                    try:
                        # Wait for the reload to complete (location.reload() from challenge script)
                        await page.wait_for_load_state("networkidle", timeout=10000)
                        await asyncio.sleep(1)  # Give it a moment to settle
                        challenge_solved = True
                        logger.debug("Page reloaded after challenge solved")
                        break
                    except Exception as e:
                        logger.debug(f"Waiting for page reload: {e}")
                        # Continue waiting

                await asyncio.sleep(wait_interval)
                waited += wait_interval

            if not challenge_solved:
                logger.warning(f"Challenge may not have solved after {max_wait_time}s, proceeding anyway")

            # Wait a bit more for any dynamic content to load
            await page.wait_for_timeout(2000)

            # Get the full page HTML - this contains all products, not just a paginated subset
            # The JSON response only returns a limited set of products, so we use the full page
            content = await page.content()
            logger.debug("Retrieved full page HTML after challenge solved")
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
            if "page" in (url or ""):
                return soup  # Only modify product pages
            # Find product section
            product_section = soup.select("div.product__grid")
            if len(product_section) > 0:
                logger.info(f"Found product section for URL {url}")
                return product_section[0]
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
            return []

        # Get product grid
        product_grid = soup.select("ul.catalogGrid")
        if len(product_grid) == 0:
            logger.warning(f"No product grid found for store URL {store_url}")
            return []
        # Get all product URLs using the base class method
        product_urls_el = product_grid[0].select('a.catalogCard-image')
        product_urls = [el.get("href") for el in product_urls_el]

        # Filter out excluded products
        excluded_products = []

        filtered_urls = []
        for url in product_urls:
            if url and isinstance(url, str) and not any(excluded in url.lower() for excluded in excluded_products):
                filtered_urls.append(self.resolve_url(url ))

        return list(set(filtered_urls))
