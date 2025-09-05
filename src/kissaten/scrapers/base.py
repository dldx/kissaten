"""Base scraper abstract class."""

import asyncio
import json
import logging
import re
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
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
        if bean.origins[0].process:
            clean_process = re.sub(r"[^a-zA-Z0-9\-_]", "_", bean.origins[0].process)
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

    async def download_and_save_image(self, image_url: str, bean_uid: str, output_dir: Path) -> Path | None:
        """Download and save product image.

        Args:
            image_url: URL of the image to download
            bean_uid: Unique identifier for the bean (same as JSON filename without extension)
            output_dir: Base output directory

        Returns:
            Path to the saved image file or None if failed
        """
        try:
            # Use session datetime if available, otherwise current time
            session_datetime = self.session_datetime or datetime.now().strftime("%Y%m%d")

            bean_dir = output_dir / "roasters" / self.roaster_name.replace(" ", "_").lower() / session_datetime
            bean_dir.mkdir(parents=True, exist_ok=True)

            # Create image filename with same base name as JSON
            image_filename = bean_dir / f"{bean_uid}.png"

            # Download the image
            logger.debug(f"Downloading image: {image_url}")
            response = await self.client.get(image_url)
            response.raise_for_status()

            # Save the image as PNG
            with open(image_filename, "wb") as f:
                f.write(response.content)

            logger.debug(f"Saved image to: {image_filename}")
            return image_filename

        except Exception as e:
            logger.warning(f"Failed to download image {image_url}: {e}")
            return None

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

    async def save_bean_with_image(self, bean: CoffeeBean, output_dir: Path) -> tuple[Path, Path | None]:
        """Save a coffee bean to JSON file and download its image.

        Args:
            bean: CoffeeBean object to save
            output_dir: Base output directory

        Returns:
            Tuple of (JSON file path, image file path or None)
        """
        # Save the JSON file
        json_path = self.save_bean_to_file(bean, output_dir)

        # Download image if URL is available
        image_path = None
        if bean.image_url:
            bean_uid = self.create_bean_uid(bean)
            image_path = await self.download_and_save_image(str(bean.image_url), bean_uid, output_dir)

        return json_path, image_path

    def _get_excluded_url_patterns(self) -> list[str]:
        """Get list of URL patterns to exclude from product URLs.

        Returns:
            List of URL patterns that indicate non-coffee products
        """
        return [
            # Clear equipment brands/models that won't be in coffee names
            "v60",
            "chemex",
            "aeropress",
            "kalita",
            "hario",
            "fellow",
            "timemore",
            "baratza",
            "comandante",
            "moccamaster",
            # Clear drinkware
            "mug",
            "cup",
            "tumbler",
            # Clear clothing
            "shirt",
            "t-shirt",
            "tee",
            "hoodie",
            "clothing",
            # Clear services
            "gift-card",
            "subscription",
            "workshop",
            # Clear non-coffee items
            "equipment",
            "grinder",
            "merch",
            "merchandise",
            # Administrative pages
            "cart",
            "checkout",
            "account",
            "login",
            "contact",
            "about",
            "shipping",
            "privacy",
            "terms",
            "admin",
            "api",
        ]

    def _get_excluded_url_path_patterns(self) -> list[str]:
        """Get list of URL path patterns to exclude.

        Returns:
            List of URL path patterns that indicate non-product pages
        """
        return [
            "/cart",
            "/checkout",
            "/account",
            "/login",
            "/contact",
            "/about",
            "/shipping",
            "/privacy",
            "/terms",
            "/admin",
            "/api",
        ]

    def is_coffee_product_url(self, url: str, required_path_patterns: list[str] | None = None) -> bool:
        """Check if a product URL is likely for coffee beans.

        Args:
            url: URL to check
            required_path_patterns: List of required path patterns (e.g., ["/products/", "/product/"])
                                  If None, will check for common product path patterns

        Returns:
            True if URL appears to be for coffee beans
        """
        if not url:
            return False

        url_lower = url.lower()

        # Check excluded patterns
        excluded_patterns = self._get_excluded_url_patterns()
        for pattern in excluded_patterns:
            if pattern in url_lower:
                return False

        # Check excluded URL path patterns
        excluded_url_patterns = self._get_excluded_url_path_patterns()
        for pattern in excluded_url_patterns:
            if pattern in url_lower:
                return False

        # Check for required product path patterns
        if required_path_patterns:
            if not any(pattern in url_lower for pattern in required_path_patterns):
                return False
        else:
            # Default check for common product patterns
            common_product_patterns = ["/product/", "/products/", "/shop/p/"]
            if not any(pattern in url_lower for pattern in common_product_patterns):
                return False

        # If it's a product URL but doesn't match coffee indicators,
        # we'll be conservative and include it (AI will filter during extraction)
        return True

    def _get_excluded_product_name_categories(self) -> list[str]:
        """Get list of product name categories to exclude.

        Returns:
            List of category keywords that indicate non-coffee products
        """
        return [
            # Clear equipment brands/models
            "grinder",
            "v60",
            "chemex",
            "aeropress",
            "kalita",
            "hario",
            "fellow",
            "timemore",
            "baratza",
            "comandante",
            "moccamaster",
            # Clear drinkware
            "mug",
            "cup",
            "tumbler",
            # Clear clothing
            "shirt",
            "t-shirt",
            "tee",
            "hoodie",
            "clothing",
            # Clear services
            "gift card",
            "subscription",
            "workshop",
            # Clear non-coffee items
            "equipment",
            "merch",
            "merchandise",
        ]

    def is_coffee_product_name(self, name: str) -> bool:
        """Check if a product name indicates coffee beans (not equipment/accessories).

        Args:
            name: Product name to check

        Returns:
            True if the product appears to be coffee beans
        """
        if not name:
            return False

        name_lower = name.lower()

        # Check excluded categories
        excluded_categories = self._get_excluded_product_name_categories()
        for category in excluded_categories:
            if category in name_lower:
                return False

        # If no clear indicators, be conservative and include it
        return True

    async def process_product_batch(
        self,
        product_urls: list[str],
        extract_function: Callable[[str], Awaitable[CoffeeBean | None]],
        batch_size: int = 2,
        save_to_file: bool = True,
        output_dir: Path | None = None,
    ) -> list[CoffeeBean]:
        """Process a batch of product URLs concurrently.

        Args:
            product_urls: List of product URLs to process
            extract_function: Function to extract bean from a product URL
            batch_size: Number of URLs to process concurrently
            save_to_file: Whether to save beans to individual files
            output_dir: Output directory for saving files

        Returns:
            List of successfully extracted CoffeeBean objects
        """
        coffee_beans = []

        if output_dir is None:
            output_dir = Path("data")

        # Process products in batches
        for i in range(0, len(product_urls), batch_size):
            batch_urls = product_urls[i : i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(product_urls) + batch_size - 1) // batch_size
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch_urls)} products)")

            # Process this batch concurrently
            tasks = [extract_function(url) for url in batch_urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Filter out None results and exceptions
            for result in results:
                if isinstance(result, CoffeeBean):
                    coffee_beans.append(result)
                    if save_to_file:
                        # Save bean to file with image download and mark as scraped
                        await self.save_bean_with_image(result, output_dir)
                        self._mark_bean_as_scraped(str(result.url))
                elif isinstance(result, Exception):
                    logger.error(f"Exception in batch processing: {result}")

            # Small delay between batches to be respectful
            if i + batch_size < len(product_urls):
                await asyncio.sleep(0.5)

        return coffee_beans

    async def scrape_with_ai_extraction(
        self,
        extract_product_urls_function: Callable[[str], Awaitable[list[str]]],
        ai_extractor,
        use_playwright: bool = False,
        use_optimized_mode: bool = False,
        translate_to_english: bool = False,
        max_concurrent: int = 2,
        output_dir: Path | None = None,
    ) -> list[CoffeeBean]:
        """Common scraping flow with AI extraction.

        Args:
            extract_product_urls_function: Function to extract product URLs from store page
            ai_extractor: AI extractor instance
            use_playwright: Whether to use Playwright for fetching pages
            max_concurrent: Maximum number of concurrent requests (default: 2)
            output_dir: Output directory for saving files

        Returns:
            List of CoffeeBean objects
        """
        session = self.start_session()
        coffee_beans = []

        try:
            # Load existing beans for this session to avoid re-scraping
            self._load_existing_beans_for_session(output_dir)

            store_urls = self.get_store_urls()

            for store_url in store_urls:
                logger.info(f"Scraping store page: {store_url}")

                # Extract product URLs
                product_urls = await extract_product_urls_function(store_url)
                logger.info(f"Found {len(product_urls)} total product URLs on {store_url}")

                session.pages_scraped += 1

                # Filter out URLs that have already been scraped in this session
                new_product_urls = [url for url in product_urls if not self._is_bean_already_scraped(url)]
                skipped_count = len(product_urls) - len(new_product_urls)

                if skipped_count > 0:
                    logger.info(f"Skipping {skipped_count} already scraped products from today's session")
                logger.info(f"Processing {len(new_product_urls)} new products")

                # Create semaphore to limit concurrent processing
                semaphore = asyncio.Semaphore(max_concurrent)

                # Define extraction function with semaphore control
                async def extract_bean_from_url_with_semaphore(product_url: str) -> CoffeeBean | None:
                    async with semaphore:
                        try:
                            logger.debug(f"AI extracting from: {product_url}")
                            product_soup = await self.fetch_page(product_url, use_playwright=use_playwright)

                            if not product_soup:
                                logger.warning(f"Failed to fetch product page: {product_url}")
                                return None

                            session.pages_scraped += 1

                            # Use AI to extract detailed bean information
                            bean = await self._extract_bean_with_ai(
                                ai_extractor,
                                product_soup,
                                product_url,
                                use_optimized_mode=use_optimized_mode,
                                translate_to_english=translate_to_english,
                            )
                            if bean and self.is_coffee_product_name(bean.name):
                                origins_str = ", ".join(str(origin) for origin in bean.origins)
                                logger.debug(f"AI extracted: {bean.name} from {origins_str}")
                                # Save bean to file and mark as scraped
                                if output_dir is None:
                                    output_dir_to_use = Path("data")
                                else:
                                    output_dir_to_use = output_dir
                                await self.save_bean_with_image(bean, output_dir_to_use)
                                self._mark_bean_as_scraped(product_url)
                                return bean

                            return None

                        except Exception as e:
                            logger.error(f"Error processing product {product_url}: {e}")
                            return None

                # Process all products concurrently with semaphore control
                logger.info(
                    f"Processing {len(new_product_urls)} products with max {max_concurrent} concurrent requests"
                )
                tasks = [extract_bean_from_url_with_semaphore(url) for url in new_product_urls]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Filter out None results and exceptions
                for result in results:
                    if isinstance(result, CoffeeBean):
                        coffee_beans.append(result)
                    elif isinstance(result, Exception):
                        logger.error(f"Exception in concurrent processing: {result}")

            session.beans_found = len(coffee_beans)
            session.beans_processed = len(coffee_beans)

            self.end_session(success=True)

        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            session.add_error(f"Scraping error: {e}")
            self.end_session(success=False)
            raise

        return coffee_beans

    async def _extract_bean_with_ai(
        self,
        ai_extractor,
        soup: BeautifulSoup,
        product_url: str,
        use_optimized_mode: bool = False,
        translate_to_english: bool = False,
    ) -> CoffeeBean | None:
        """Common AI extraction logic.

        Args:
            ai_extractor: AI extractor instance
            soup: BeautifulSoup object of the product page
            product_url: URL of the product page
            use_optimized_mode: Whether to use optimized mode (with screenshots)
            translate_to_english: Whether to translate results to English

        Returns:
            CoffeeBean object or None if extraction fails
        """
        try:
            # Get the HTML content for AI processing
            html_content = str(soup)

            # Use AI extractor to get structured data
            if use_optimized_mode:
                # For complex sites that benefit from visual analysis
                screenshot_bytes = await self.take_screenshot(product_url)
                bean: CoffeeBean = await ai_extractor.extract_coffee_data(
                    html_content, product_url, screenshot_bytes, use_optimized_mode=True
                )
            else:
                # Standard mode for most sites
                bean: CoffeeBean = await ai_extractor.extract_coffee_data(html_content, product_url)

            # if we don't have country and process and variety, then we probably don't have a valid bean
            if not bean.origins[0].country and not bean.origins[0].process and not bean.origins[0].variety:
                logger.warning(f"Failed to extract data from {product_url}")
                return None

            if bean:
                logger.debug(f"AI extracted: {bean.name} from {', '.join(str(origin) for origin in bean.origins)}")
                if translate_to_english:
                    bean = await ai_extractor.translate_to_english(bean)
                return bean
            else:
                logger.warning(f"Failed to extract data from {product_url}")
                return None

        except Exception as e:
            logger.error(f"Error extracting bean from product page {product_url}: {e}")
            return None

    def extract_product_urls_from_soup(
        self, soup: BeautifulSoup, url_path_patterns: list[str], selectors: list[str] | None = None
    ) -> list[str]:
        """Extract product URLs from a soup object using common patterns.

        Args:
            soup: BeautifulSoup object to extract URLs from
            url_path_patterns: Required URL path patterns (e.g., ["/products/", "/product/"])
            selectors: Optional CSS selectors to try for finding product links

        Returns:
            List of product URLs
        """
        product_urls = []

        # Default selectors if none provided
        if selectors is None:
            selectors = [
                'a[href*="/product/"]',
                'a[href*="/products/"]',
                ".product-link",
                ".product-item a",
                ".product a",
                'a[href*="/shop/p/"]',
            ]

        # Try each selector
        for selector in selectors:
            try:
                links = soup.select(selector)
                if links:
                    for link in links:
                        if hasattr(link, "get"):
                            href = link.get("href")
                            if href and isinstance(href, str):
                                full_url = self.resolve_url(href)
                                if self.is_coffee_product_url(full_url, url_path_patterns):
                                    product_urls.append(full_url)
                    break  # Use first successful selector
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")

        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in product_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        return unique_urls

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
