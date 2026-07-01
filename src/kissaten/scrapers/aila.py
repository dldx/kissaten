"""Aila coffee roasters scraper implementation with AI-powered extraction."""

import logging

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="aila",
    display_name="Aila",
    roaster_name="Aila",
    website="https://www.ailacoffee.com",
    description="Specialty coffee roaster based in Switzerland offering single-origin coffees "
    "from Latin America and Africa",
    requires_api_key=True,
    currency="CHF",
    country="Switzerland",
    status="available",
)
class AilaScraper(BaseScraper):
    """Scraper for Aila (ailacoffee.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Aila scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Aila",
            base_url="https://www.ailacoffee.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List of paginated listing pages
        """
        return [
            "https://www.ailacoffee.com/",
            "https://www.ailacoffee.com/?page=2",
        ]

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
            use_optimized_mode=True,
        )

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Force currency to CHF since the site doesn't expose it via meta tags."""
        bean.currency = "CHF"
        return super().postprocess_extracted_bean(bean)

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page and return its BeautifulSoup object.

        For product pages, narrow the returned soup to the single
        ``<article>`` element so the AI extractor only sees the product
        detail (cuts token count dramatically on Squarespace pages that
        include the full site chrome).

        Args:
            url: URL of the page to fetch
            use_playwright: Whether to use Playwright for fetching

        Returns:
            BeautifulSoup/Tag of the page, or None if fetch failed
        """
        url = kwargs.get("url")
        if not url and len(args) > 0:
            url = args[0]

        try:
            soup = await super().fetch_page(*args, **kwargs)
            if "/product-page/" not in (url or ""):
                return soup  # Only narrow product pages
            article = soup.select_one("article") if soup else None
            if article is not None:
                return article
            logger.warning(f"No <article> found for product URL {url}")
            return soup
        except Exception as e:
            logger.error(f"Error fetching page {url}: {e}")
            return None

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from a Squarespace listing page.

        Aila uses Squarespace. Products are rendered server-side on paginated
        listing pages (``?page=2``, etc.). Each product sits in a
        ``<li data-hook="product-list-grid-item">`` card, with an
        ``Out of Stock`` span inside the same card when the SKU is no longer
        purchasable — we use that as the sold-out signal before any URL
        filtering.

        Args:
            store_url: URL of the store page (with or without ``?page=N``)

        Returns:
            List of in-stock product URLs
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        # Sold-out detection: text — Squarespace renders an ``Out of Stock``
        # span inside the same product <li> card. Iterate cards directly,
        # before running is_coffee_product_url, so excluded products can't
        # leak past the stock check.
        product_urls: list[str] = []
        excluded_products = [
            "subscription",  # Subscription SKUs
            "gift-card",  # Gift cards
            "giftcard",  # Gift cards (no hyphen variant)
            "course",  # Courses
            "workshop",  # Workshops
            "merch",  # Merchandise
            "equipment",  # Brewing equipment
            "filter-papers",  # Paper filters
        ]

        seen: set[str] = set()
        for card in soup.select("li[data-hook='product-list-grid-item']"):
            if not isinstance(card, Tag):
                continue

            is_sold_out = any(
                s.get_text(strip=True).lower() in ("out of stock", "sold out")
                for s in card.find_all("span")
            )
            if is_sold_out:
                logger.debug(f"Skipping sold-out product on {store_url}")
                continue

            link = card.select_one("a[href*='/product-page/']")
            if not isinstance(link, Tag):
                continue
            href = link.get("href")
            if not href or not isinstance(href, str):
                continue
            href = href.split("?")[0]
            product_url = self.resolve_url(href)
            if product_url in seen:
                continue

            url_lower = product_url.lower()
            if any(excluded in url_lower for excluded in excluded_products):
                logger.debug(f"Excluding non-coffee product URL: {product_url}")
                continue

            if self.is_coffee_product_url(product_url, required_path_patterns=["/product-page/"]):
                seen.add(product_url)
                product_urls.append(product_url)

        logger.info(
            f"Found {len(product_urls)} in-stock coffee product URLs on {store_url}"
        )
        return product_urls
