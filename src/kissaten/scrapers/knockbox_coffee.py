"""Knockbox Coffee scraper implementation with AI-powered extraction."""

import logging

from bs4 import BeautifulSoup

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="knockbox",
    display_name="Knockbox",
    roaster_name="Knockbox",
    website="https://www.knockboxcoffee.hk",
    description="Specialty coffee roaster and cafe based in Mong Kok, Hong Kong",
    requires_api_key=True,
    currency="HKD",
    country="Hong Kong",
    status="available",
)
class KnockboxScraper(BaseScraper):
    """Scraper for Knockbox (knockboxcoffee.hk) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Knockbox scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Knockbox",
            base_url="https://www.knockboxcoffee.hk",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the paginated coffee collection URLs
        """
        return [
            "https://www.knockboxcoffee.hk/coffee",
            "https://www.knockboxcoffee.hk/coffee?page=2",
        ]

    async def fetch_page(self, url: str, retries: int = 0, use_playwright: bool = False):
        """Fetch a page and trim the soup to the useful product description for product pages.

        Wix renders the Knockbox product description inside a TPA section
        (``div[id^="TPAMultiSection_"]``). Everything else on the page is
        site chrome, scripts, or the "Related Products" carousel, which only
        bloats the AI extractor prompt. For product pages we keep only that
        TPA container; for everything else we return the full soup unchanged.

        Args:
            url: URL to fetch
            retries: Retry count
            use_playwright: Whether to use Playwright

        Returns:
            BeautifulSoup object or None
        """
        soup = await super().fetch_page(url, retries=retries, use_playwright=use_playwright)
        if soup and "/product-page/" in url:
            container = None
            for el in soup.select('div[id^="TPAMultiSection_"]'):
                eid = el.get("id", "")
                # Sub-sections of the TPA widget use dotted ids like
                # "TPAMultiSection_xxx.product-page-top" and loadable chunks
                # use "__LOADABLE_REQUIRED_CHUNKS__" suffixes; skip those and
                # keep only the bare TPA container with real text content.
                if "." in eid or "__" in eid:
                    continue
                if el.get_text(strip=True):
                    container = el
                    break
            if container is not None:
                logger.debug(
                    f"Trimmed product page soup to TPA container for {url} "
                    f"({len(str(container))} chars)"
                )
                return BeautifulSoup(str(container), "lxml")
        return soup

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
            use_optimized_mode=False,
        )

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from store page.

        Sold-out detection: text detection — Wix renders "Out of stock" inside
        the product card's text container, so we walk the link's ancestor tree
        and drop any link whose ancestor text contains "Out of stock".

        Args:
            store_url: URL of the store page

        Returns:
            List of in-stock coffee product URLs
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        candidate_links = soup.select('a[href*="/product-page/"]')

        # Roaster-specific URL exclusions (complements base class list).
        roaster_excludes = [
            "capsule",
            "drip-bag",
            "tool",
            "glass",
            "machine",
            "outin",
            "subscript",
            "ico",
        ]

        product_urls = []
        seen = set()
        for link in candidate_links:
            href = link.get("href")
            if not href or not isinstance(href, str):
                continue
            full_url = self.resolve_url(href)
            if full_url in seen:
                continue

            # Sold-out filtering must run before is_coffee_product_url so
            # excluded products do not leak past the stock check. Wix renders
            # "Out of stock" inside the product card text container which is
            # the link's nearest ancestor with substantial text. Walking too
            # far up reaches the <ul> holding all products (which always
            # contains "Out of stock" from genuinely sold-out items), so we
            # stop at the product card: the first ancestor whose text is
            # under 400 chars.
            sold_out = False
            ancestor = link
            for _ in range(4):
                ancestor = ancestor.parent
                if ancestor is None:
                    break
                card_text = ancestor.get_text(" ", strip=True)
                if not card_text:
                    continue
                if len(card_text) > 400:
                    # Past the product card into the list of all products.
                    break
                if "Out of stock" in card_text:
                    sold_out = True
                    break
            if sold_out:
                logger.debug(f"Skipping sold-out product: {full_url}")
                continue

            url_lower = full_url.lower()
            if any(term in url_lower for term in roaster_excludes):
                logger.debug(f"Excluding non-coffee product URL: {full_url}")
                continue

            if not self.is_coffee_product_url(full_url, required_path_patterns=["/product-page/"]):
                continue

            seen.add(full_url)
            product_urls.append(full_url)

        logger.info(
            f"Found {len(product_urls)} in-stock coffee product URLs on {store_url}"
        )
        return product_urls
