"""YES PLZ scraper implementation with AI-powered extraction (custom Next.js site)."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="yes-plz",
    display_name="YES PLZ",
    roaster_name="YES PLZ",
    website="https://www.yesplz.coffee",
    description=(
        "Los Angeles-based subscription roaster roasting a new unique blend every "
        "week, plus rotating single origin, espresso and decaf releases."
    ),
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class YesPlzScraper(BaseScraper):
    """Scraper for YES PLZ (yesplz.coffee) — a small custom Next.js storefront.

    The whole shop is a fixed set of server-rendered product pages (The Mix,
    Single Origin, Homestar Espresso, Decaf, Fermentation Project) linked from
    the ``/shop`` page. All content is present in the initial HTML, so no
    Playwright is needed. YES PLZ also participates in the Fermentation Project
    tasting kit via ``/product/fermentation-project``.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize YES PLZ scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="YES PLZ",
            base_url="https://www.yesplz.coffee",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = None
        try:
            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
        except ValueError:
            logger.warning("Google API key not configured. AI extraction will not be available.")

    async def get_store_urls(self) -> list[str]:
        """Return the shop listing URL."""
        return ["https://www.yesplz.coffee/shop"]

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
            use_playwright=False,  # Product pages are fully server-rendered
            use_optimized_mode=False,
            translate_to_english=False,  # Site is in English
        )

    # Sold-out detection: the /shop listing renders category-style cards with
    # no stock state at all, so checklist steps 1-3 cannot run at listing
    # level. Stock state only appears on the product detail page as a visible
    # "SOLD OUT" banner (e.g. the Fermentation Project pre-sale). Since the
    # catalog is tiny (5 pages), we fetch each detail page during URL
    # extraction and skip products whose visible text contains the marker —
    # scripts/styles are stripped first so embedded JSON cannot false-positive.
    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract in-stock product URLs from the /shop listing page.

        Args:
            store_url: URL of the shop listing page

        Returns:
            List of in-stock coffee product URLs
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        product_urls: list[str] = []
        seen: set[str] = set()
        for link in soup.select('a[href*="/product/"]'):
            href = link.get("href")
            if not href or not isinstance(href, str):
                continue
            url = self.resolve_url(href.split("?")[0].split("#")[0])

            # Apply coffee-product URL filtering (uses the /product/ path)
            if not self.is_coffee_product_url(url, required_path_patterns=["/product/"]):
                continue

            if url not in seen:
                seen.add(url)
                product_urls.append(url)

        logger.info(f"Found {len(product_urls)} product URLs from {store_url}")

        # Detail-level sold-out check (visible "SOLD OUT" banner).
        in_stock_urls: list[str] = []
        for url in product_urls:
            detail_soup = await self.fetch_page(url)
            if not detail_soup:
                logger.warning(f"Could not fetch detail page for stock check, keeping: {url}")
                in_stock_urls.append(url)
                continue
            for tag in detail_soup(["script", "style"]):
                tag.decompose()
            visible_text = detail_soup.get_text(" ", strip=True).lower()
            if "sold out" in visible_text:
                logger.debug(f"Skipping sold-out product: {url}")
                continue
            in_stock_urls.append(url)

        logger.info(f"Found {len(in_stock_urls)} in-stock product URLs from {store_url}")
        return in_stock_urls

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Pin USD as the store currency (default-currency-GBP fallback guard)."""
        bean.currency = "USD"
        return bean
