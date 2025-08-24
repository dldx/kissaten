"""Base scraper abstract class."""

import asyncio
import json
import logging
import re
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from playwright.async_api import Browser, Page, async_playwright

from ..schemas import CoffeeBean, ScrapingSession

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Abstract base class for all coffee roaster scrapers."""

    def __init__(
        self,
        roaster_name: str,
        base_url: str,
        rate_limit_delay: float = 1.0,
        max_retries: int = 3,
        timeout: float = 30.0,
        custom_headers: dict[str, str] | None = None,
    ):
        """Initialize the scraper.

        Args:
            roaster_name: Name of the roaster
            base_url: Base URL for the roaster's website
            rate_limit_delay: Delay between requests in seconds
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds
            custom_headers: Custom HTTP headers to include
        """
        self.roaster_name = roaster_name
        self.base_url = base_url.rstrip("/")
        self.rate_limit_delay = rate_limit_delay
        self.max_retries = max_retries
        self.timeout = timeout

        # Default headers
        self.headers = {
            "User-Agent": "Kissaten Coffee Scraper 1.0 (github.com/kissaten)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        if custom_headers:
            self.headers.update(custom_headers)

        # Initialize HTTP client
        self.client = httpx.AsyncClient(headers=self.headers, timeout=self.timeout, follow_redirects=True)

        # Playwright browser instance (lazy initialization)
        self._playwright = None
        self._browser: Browser | None = None

        # Session tracking
        self.session: ScrapingSession | None = None
        self.session_datetime: str | None = None
        self._existing_bean_files: set[str] = set()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def close(self):
        """Close the HTTP client and browser."""
        if self.client:
            await self.client.aclose()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    def start_session(self) -> ScrapingSession:
        """Start a new scraping session."""
        self.session_datetime = datetime.now().strftime("%Y%m%d")
        session_id = f"{self.roaster_name}_{self.session_datetime}"
        self.session = ScrapingSession(
            session_id=session_id,
            roaster_name=self.roaster_name,
            scraper_version="1.0",
            started_at=datetime.now(),
            ended_at=None,
            success=False,
            config_used=None,
            duration_seconds=None,
            pages_scraped=0,
            requests_made=0,
            beans_found=0,
            beans_processed=0,
        )
        logger.info(f"Started scraping session: {session_id}")
        return self.session

    def end_session(self, success: bool = True):
        """End the current scraping session."""
        if self.session:
            self.session.mark_completed(success)
            logger.info(
                f"Ended session {self.session.session_id}: success={success}, beans_found={self.session.beans_found}"
            )

    async def _get_browser(self) -> Browser:
        """Get or initialize the Playwright browser instance.

        Returns:
            Browser instance
        """
        if not self._browser:
            if not self._playwright:
                self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--no-first-run",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                ],
            )
        return self._browser

    async def _fetch_with_playwright(self, url: str) -> str:
        """Fetch page content using Playwright.

        Args:
            url: URL to fetch

        Returns:
            HTML content as string

        Raises:
            Exception: If fetch fails
        """
        browser = await self._get_browser()
        page: Page = await browser.new_page()

        try:
            # Set user agent and other headers
            await page.set_extra_http_headers(self.headers)

            # Navigate to the page
            response = await page.goto(url, timeout=self.timeout * 1000, wait_until="domcontentloaded")

            if not response or not response.ok:
                raise Exception(f"Failed to load page: {response.status if response else 'No response'}")

            # Wait a bit for dynamic content to load
            await page.wait_for_timeout(1000)

            # Get the page content
            content = await page.content()
            return content

        finally:
            await page.close()

    async def take_screenshot(self, url: str, full_page: bool = True) -> bytes | None:
        """Take a screenshot of a webpage using Playwright.

        Args:
            url: URL to take screenshot of
            full_page: Whether to take a full page screenshot or just viewport

        Returns:
            Screenshot as bytes or None if failed
        """
        browser = await self._get_browser()
        page: Page = await browser.new_page()

        try:
            # Set user agent and other headers
            await page.set_extra_http_headers(self.headers)

            # Navigate to the page
            response = await page.goto(url, timeout=self.timeout * 1000, wait_until="domcontentloaded")

            if not response or not response.ok:
                raise Exception(f"Failed to load page: {response.status if response else 'No response'}")

            # Wait a bit for dynamic content to load
            await page.wait_for_timeout(2000)

            # Take screenshot
            screenshot_bytes = await page.screenshot(full_page=full_page, type="png")
            logger.debug(f"Successfully took screenshot of: {url}")
            return screenshot_bytes

        except Exception as e:
            logger.error(f"Failed to take screenshot of {url}: {e}")
            return None

        finally:
            await page.close()

    async def fetch_page_with_screenshot(
        self, url: str, retries: int = 0, use_playwright: bool = False
    ) -> tuple[BeautifulSoup | None, bytes | None]:
        """Fetch a web page and optionally take a screenshot.

        Args:
            url: URL to fetch
            retries: Number of retries attempted
            use_playwright: Whether to use Playwright instead of httpx

        Returns:
            Tuple of (BeautifulSoup object, screenshot bytes) or (None, None) if failed
        """
        soup = await self.fetch_page(url, retries, use_playwright)
        screenshot = None

        if soup and use_playwright:
            # Take a screenshot when using Playwright
            screenshot = await self.take_screenshot(url)

        return soup, screenshot

    async def fetch_page(self, url: str, retries: int = 0, use_playwright: bool = False) -> BeautifulSoup | None:
        """Fetch and parse a web page.

        Args:
            url: URL to fetch
            retries: Number of retries attempted
            use_playwright: Whether to use Playwright instead of httpx

        Returns:
            BeautifulSoup object or None if failed
        """
        try:
            # Rate limiting
            if retries == 0:  # Don't delay on retries
                await asyncio.sleep(self.rate_limit_delay)

            if use_playwright:
                # Use Playwright for JavaScript-heavy sites
                logger.debug(f"Fetching with Playwright: {url}")
                html_content = await self._fetch_with_playwright(url)
            else:
                # Use httpx for simple sites
                logger.debug(f"Fetching with httpx: {url}")
                response = await self.client.get(url)
                response.raise_for_status()
                html_content = response.text

            # Track requests
            if self.session:
                self.session.requests_made += 1

            # Parse HTML
            soup = BeautifulSoup(html_content, "lxml")
            logger.debug(f"Successfully fetched: {url}")
            return soup

        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP error {e.response.status_code} for {url}")
            if self.session:
                self.session.add_error(f"HTTP {e.response.status_code}: {url}")

        except httpx.RequestError as e:
            logger.warning(f"Request error for {url}: {e}")
            if self.session:
                self.session.add_error(f"Request error: {url} - {e}")

        except Exception as e:
            error_msg = f"Unexpected error fetching {url}: {e}"
            logger.error(error_msg)
            if self.session:
                self.session.add_error(f"Unexpected error: {url} - {e}")

            # If Playwright failed and this wasn't a retry with httpx, try httpx as fallback
            if use_playwright and retries == 0:
                logger.info(f"Playwright failed for {url}, falling back to httpx")
                return await self.fetch_page(url, retries, use_playwright=False)

        # Retry logic
        if retries < self.max_retries:
            logger.info(f"Retrying {url} (attempt {retries + 1}/{self.max_retries})")
            await asyncio.sleep(2**retries)  # Exponential backoff
            return await self.fetch_page(url, retries + 1, use_playwright)

        return None

    def resolve_url(self, url: str) -> str:
        """Resolve relative URLs to absolute URLs.

        Args:
            url: URL to resolve

        Returns:
            Absolute URL
        """
        if not url:
            return url

        # If already absolute, return as-is
        if urlparse(url).netloc:
            return url

        # Join with base URL
        return urljoin(self.base_url, url)

    def clean_text(self, text: str | None) -> str | None:
        """Clean and normalize text content.

        Args:
            text: Text to clean

        Returns:
            Cleaned text or None
        """
        if not text:
            return None

        # Remove extra whitespace and normalize
        cleaned = " ".join(text.strip().split())
        return cleaned if cleaned else None

    def extract_price(self, price_text: str) -> float | None:
        """Extract numeric price from text.

        Args:
            price_text: Text containing price

        Returns:
            Extracted price as float or None
        """
        import re

        if not price_text:
            return None

        # Remove currency symbols and extract numbers
        price_match = re.search(r"[\d,]+\.?\d*", price_text.replace(",", ""))
        if price_match:
            try:
                return float(price_match.group())
            except ValueError:
                pass

        return None

    def extract_weight(self, weight_text: str) -> int | None:
        """Extract weight in grams from text.

        Args:
            weight_text: Text containing weight

        Returns:
            Weight in grams or None
        """
        import re

        if not weight_text:
            return None

        # Look for weight patterns
        weight_patterns = [
            r"(\d+)\s*g(?:ram)?s?",  # 250g, 250 grams
            r"(\d+)\s*oz",  # 12oz
            r"(\d+)\s*lb",  # 1lb
            r"(\d+)\s*kg",  # 1kg
        ]

        weight_text_lower = weight_text.lower()

        for pattern in weight_patterns:
            match = re.search(pattern, weight_text_lower)
            if match:
                value = int(match.group(1))

                # Convert to grams
                if "oz" in pattern:
                    return int(value * 28.35)  # oz to grams
                elif "lb" in pattern:
                    return int(value * 453.59)  # lb to grams
                elif "kg" in pattern:
                    return value * 1000  # kg to grams
                else:
                    return value  # already in grams

        return None

    def create_bean_uid(self, bean: CoffeeBean) -> str:
        """Create a unique identifier for a coffee bean.

        Args:
            bean: CoffeeBean object

        Returns:
            Unique identifier suitable for filename
        """
        # Start with the bean name
        name = bean.name or "unknown"

        # Clean the name for use as filename
        # Replace spaces and special characters with underscores
        clean_name = re.sub(r"[^a-zA-Z0-9\-_]", "_", name)
        # Remove multiple consecutive underscores
        clean_name = re.sub(r"_+", "_", clean_name)
        # Remove leading/trailing underscores
        clean_name = clean_name.strip("_")

        # Add process if available
        process_part = ""
        if bean.process:
            clean_process = re.sub(r"[^a-zA-Z0-9\-_]", "_", bean.process)
            clean_process = re.sub(r"_+", "_", clean_process).strip("_")
            process_part = f"_{clean_process}"

        # Create base filename
        base_name = f"{clean_name}{process_part}".lower()

        # Ensure it's not too long (max 100 chars before timestamp)
        if len(base_name) > 100:
            base_name = base_name[:100]

        # Add timestamp for uniqueness
        timestamp = datetime.now().strftime("%H%M%S")

        return f"{base_name}_{timestamp}"

    def _get_session_bean_dir(self, output_dir: Path) -> Path:
        """Get the bean directory for the current session.

        Args:
            output_dir: Base output directory

        Returns:
            Path to the session's bean directory
        """
        session_datetime = self.session_datetime or datetime.now().strftime("%Y%m%d")
        return output_dir / "roasters" / self.roaster_name.replace(" ", "_").lower() / session_datetime

    def _load_existing_beans_for_session(self, output_dir: Path | None = None) -> None:
        """Load existing bean files for the current session to avoid re-scraping.

        Args:
            output_dir: Base output directory (defaults to 'data')
        """
        if output_dir is None:
            output_dir = Path("data")

        session_dir = self._get_session_bean_dir(output_dir)

        if session_dir.exists():
            # Load all existing bean files from this session
            for bean_file in session_dir.glob("*.json"):
                try:
                    with open(bean_file, encoding="utf-8") as f:
                        bean_data = json.loads(f.read())
                        bean_url = bean_data.get("url", "")
                        if bean_url:
                            self._existing_bean_files.add(bean_url)
                            logger.debug(f"Found existing bean file for URL: {bean_url}")
                except Exception as e:
                    logger.warning(f"Failed to read existing bean file {bean_file}: {e}")

        logger.info(f"Loaded {len(self._existing_bean_files)} existing beans for session {self.session_datetime}")

    def _is_bean_already_scraped(self, product_url: str) -> bool:
        """Check if a bean has already been scraped in this session.

        Args:
            product_url: URL of the product to check

        Returns:
            True if bean already exists for this session
        """
        return product_url in self._existing_bean_files

    def _mark_bean_as_scraped(self, product_url: str) -> None:
        """Mark a bean URL as scraped for this session.

        Args:
            product_url: URL of the scraped product
        """
        self._existing_bean_files.add(product_url)

    def save_bean_to_file(self, bean: CoffeeBean, output_dir: Path) -> Path:
        """Save a single coffee bean to its own JSON file.

        Args:
            bean: CoffeeBean object to save
            output_dir: Base output directory

        Returns:
            Path to the saved file
        """
        # Use session datetime if available, otherwise current time
        session_datetime = self.session_datetime or datetime.now().strftime("%Y%m%d")

        bean_dir = output_dir / "roasters" / self.roaster_name.replace(" ", "_").lower() / session_datetime
        bean_dir.mkdir(parents=True, exist_ok=True)

        # Create unique filename
        bean_uid = self.create_bean_uid(bean)
        filename = bean_dir / f"{bean_uid}.json"


        # Save to file
        with open(filename, "w") as f:
            f.write(bean.model_dump_json(indent=2))

        logger.debug(f"Saved bean to: {filename}")
        return filename

    def save_beans_individually(self, beans: list[CoffeeBean], output_dir: Path | None = None) -> list[Path]:
        """Save all beans to individual JSON files.

        Args:
            beans: List of CoffeeBean objects
            output_dir: Base output directory (defaults to 'data')

        Returns:
            List of paths to saved files
        """
        if output_dir is None:
            output_dir = Path("data")

        saved_files = []
        for bean in beans:
            try:
                file_path = self.save_bean_to_file(bean, output_dir)
                saved_files.append(file_path)
            except Exception as e:
                logger.error(f"Failed to save bean {bean.name}: {e}")

        return saved_files

    @abstractmethod
    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from the roaster's website.

        This method must be implemented by each roaster scraper.

        Returns:
            List of validated CoffeeBean objects
        """
        pass

    @abstractmethod
    def get_store_urls(self) -> list[str]:
        """Get list of store URLs to scrape.

        Returns:
            List of URLs to scrape for coffee products
        """
        pass
