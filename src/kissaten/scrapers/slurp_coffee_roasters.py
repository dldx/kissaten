"""Plot Roasting scraper implementation with AI-powered extraction."""

import asyncio
import logging

from playwright.async_api import Page

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="slurp-coffee-roasters",
    display_name="Slurp Coffee Roasters",
    roaster_name="Slurp Coffee Roasters",
    website="https://slurpcoffeeroasters.com.ua/",
    description="Ukrainian specialty coffee roaster focused on high-quality beans",
    requires_api_key=True,
    currency="UAH",
    country="Ukraine",
    status="available",
)
class SlurpCoffeeRoastersScraper(BaseScraper):
    """Scraper with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Slurp Coffee Roasters",
            base_url="https://slurpcoffeeroasters.com.ua/",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the store URL
        """
        return ["https://slurpcoffeeroasters.com.ua/kava/", "https://slurpcoffeeroasters.com.ua/kava/filter/page=2/"]


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
            use_playwright=False,
            translate_to_english=True,
        )

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

        # Use the base class method with standard Shopify patterns
        product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/"],
            selectors=[
                'a.catalogCard-image:not(.__grayscale)',
            ],
        )

        excluded_products = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "accessory",
            "merchandise",
            "test-roast",
        ]
        filtered_urls = []
        for url in product_urls:
            if url and isinstance(url, str) and not any(excluded in url.lower() for excluded in excluded_products):
                filtered_urls.append(url)

        return filtered_urls
