"""Happy Barista scraper implementation with AI-powered extraction.

Happy Barista is an independent North Yorkshire (UK) specialty coffee roaster,
formerly trading as happybarista.co.uk and now serving a live WooCommerce
storefront at www.happybarista.com (canonical www). The coffee catalogue is a
small rotating set of whole-bean blends and single-origin coffees (about six
distinct coffees) plus a coffee subscription. The storefront is WordPress +
WooCommerce.
"""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="happy-barista",
    display_name="Happy Barista",
    roaster_name="Happy Barista",
    website="https://www.happybarista.com",
    description="Independent North Yorkshire specialty coffee roaster selling a "
    "rotating set of whole-bean blends and single-origin coffees plus a coffee "
    "subscription, on a WordPress/WooCommerce storefront at happybarista.com "
    "(formerly happybarista.co.uk).",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class HappyBaristaScraper(BaseScraper):
    """Scraper for Happy Barista (www.happybarista.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Happy Barista scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Happy Barista",
            base_url="https://www.happybarista.com",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=60.0,
        )

        # Store is UK/GBP native. Pin the currency defensively (the base
        # default-currency lookup keys by the *display* name and would
        # otherwise fall back to GBP anyway, but pinning guarantees the AI
        # extractor never sees a wrong geo-detected currency).
        self.store_currency = "GBP"
        self._currency_detected = True

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        The `/shop/` page is the live WooCommerce product category listing for
        the whole-bean coffee catalogue. We deliberately do NOT crawl the full
        product sitemap here: that includes sold-out beans and the coffee
        subscription, and would defeat the base-class out-of-stock diffing
        (products in the sitemap would always appear "current"). The category
        page is the authoritative in-stock list.

        Returns:
            List containing the coffee shop URL.
        """
        return ["https://www.happybarista.com/shop/"]

    async def _scrape_new_products(self, product_urls: list[str], use_optimized_mode: bool = False) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction.

        Args:
            product_urls: List of new product URLs to extract.
            use_optimized_mode: Whether to use optimized (screenshot) mode.

        Returns:
            List of newly scraped CoffeeBean objects.
        """
        if not product_urls:
            return []

        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=False,  # WooCommerce product pages are server-rendered
            use_optimized_mode=use_optimized_mode,
        )

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from the WooCommerce shop page.

        # Sold-out detection: class (WooCommerce `outofstock` card class)
        WooCommerce marks each product card (`<li class="product ...">`) with an
        ``instock`` or ``outofstock`` token in its class list. We walk the
        `ul.products` grid and skip any card whose classes contain
        ``outofstock``, before running `is_coffee_product_url` so excluded
        products can never leak past the stock check.

        Args:
            store_url: URL of the store page.

        Returns:
            List of product URLs found on the store page.
        """
        product_urls: list[str] = []
        page_url = store_url
        pages_fetched = 0

        while page_url and pages_fetched < 5:
            soup = await self.fetch_page(page_url)
            if not soup:
                logger.error(f"Failed to fetch page: {page_url}")
                break

            # The theme renders the same product cards into several grids, so
            # collect across all `ul.products` grids and deduplicate below.
            grid = soup.select("ul.products > li.product")
            logger.info(f"Found {len(grid)} product cards on {page_url}")

            for card in grid:
                # Skip sold-out cards (WooCommerce `outofstock` class).
                if "outofstock" in (card.get("class") or []):
                    logger.debug(f"Skipping sold-out product card on {page_url}")
                    continue

                link = card.select_one('a[href*="/product/"]')
                href = link.get("href") if link else None
                if not isinstance(href, str):
                    continue

                full_url = self.resolve_url(href)
                # Strip query string before checking/adding to database.
                if "?" in full_url:
                    full_url = full_url.split("?")[0]

                if self.is_coffee_product_url(full_url, required_path_patterns=["/product/"]):
                    product_urls.append(full_url)

            # WooCommerce category pagination (e.g. `/shop/page/2/`).
            next_el = soup.select_one("a.next.page-numbers, a.next")
            next_href = next_el.get("href") if next_el else None
            if not isinstance(next_href, str):
                break
            page_url = self.resolve_url(next_href)
            if "page/" not in page_url:
                break
            pages_fetched += 1

        # Deduplicate while preserving order (the theme renders duplicate cards
        # across the shop page's multiple product grids).
        seen: set[str] = set()
        unique_urls: list[str] = []
        for url in product_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        logger.info(f"Found {len(unique_urls)} product URLs from {store_url} (whole-bean, in-stock)")
        return unique_urls

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Force GBP currency and clean query strings from the URL."""
        bean.currency = "GBP"
        if bean.url and "?" in str(bean.url):
            # Clean URL to match database schema conventions without query parameters
            from urllib.parse import unquote, urlsplit, urlunsplit

            decoded = unquote(str(bean.url))
            parts = urlsplit(decoded)
            bean.url = urlunsplit(parts._replace(query=""))

        return super().postprocess_extracted_bean(bean)
