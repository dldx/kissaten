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

        # Session tracking
        self.session: ScrapingSession | None = None
        self.session_datetime: str | None = None

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def close(self):
        """Close the HTTP client."""
        if self.client:
            await self.client.aclose()

    def start_session(self) -> ScrapingSession:
        """Start a new scraping session."""
        self.session_datetime = datetime.now().strftime("%Y%m%d")
        session_id = f"{self.roaster_name}_{self.session_datetime}"
        self.session = ScrapingSession(
            session_id=session_id,
            roaster_name=self.roaster_name,
            scraper_version="1.0",
            started_at=datetime.now(),
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

    async def fetch_page(self, url: str, retries: int = 0) -> BeautifulSoup | None:
        """Fetch and parse a web page.

        Args:
            url: URL to fetch
            retries: Number of retries attempted

        Returns:
            BeautifulSoup object or None if failed
        """
        try:
            # Rate limiting
            if retries == 0:  # Don't delay on retries
                await asyncio.sleep(self.rate_limit_delay)

            # Make request
            response = await self.client.get(url)
            response.raise_for_status()

            # Track requests
            if self.session:
                self.session.requests_made += 1

            # Parse HTML
            soup = BeautifulSoup(response.text, "lxml")
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
            logger.error(f"Unexpected error fetching {url}: {e}")
            if self.session:
                self.session.add_error(f"Unexpected error: {url} - {e}")

        # Retry logic
        if retries < self.max_retries:
            logger.info(f"Retrying {url} (attempt {retries + 1}/{self.max_retries})")
            await asyncio.sleep(2**retries)  # Exponential backoff
            return await self.fetch_page(url, retries + 1)

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

    def save_bean_to_file(self, bean: CoffeeBean, output_dir: Path) -> Path:
        """Save a single coffee bean to its own JSON file.

        Args:
            bean: CoffeeBean object to save
            output_dir: Base output directory

        Returns:
            Path to the saved file
        """
        # Create the directory structure: data/roasters/<roaster_name>/<datetime>/
        roaster_name = bean.roaster.replace(" ", "_").lower()
        # Use session datetime if available, otherwise current time
        session_datetime = self.session_datetime or datetime.now().strftime("%Y%m%d")

        bean_dir = output_dir / "roasters" / roaster_name / session_datetime
        bean_dir.mkdir(parents=True, exist_ok=True)

        # Create unique filename
        bean_uid = self.create_bean_uid(bean)
        filename = bean_dir / f"{bean_uid}.json"


        # Save to file
        with open(filename, "w", encoding="utf-8") as f:
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
