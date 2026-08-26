"""Casa Coffee Roasters scraper implementation with AI-powered extraction.

Casa Coffee Roasters (rebrand of former Casa Espresso/Casa Coffee) is an
independent Yorkshire specialty roaster based in the Bradford/Shipley area,
selling on a WordPress + WooCommerce storefront at casacoffeeroasters.co.uk.
The coffee catalogue is a rotating set of core espresso blends and single-origin
discovery coffees, plus curated sample packs for both ranges.
"""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="casa",
    display_name="Casa Coffee Roasters",
    roaster_name="Casa Coffee Roasters",
    website="https://casacoffeeroasters.co.uk",
    description="Independent Yorkshire specialty coffee roaster based in the Bradford/Shipley "
    "area, offering core espresso blends and rotating single-origin discovery coffees "
    "plus curated sample packs for both ranges (WooCommerce storefront).",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class CasaCoffeeRoastersScraper(BaseScraper):
    """Scraper for Casa Coffee Roasters (casacoffeeroasters.co.uk) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Casa Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Casa Coffee Roasters",
            base_url="https://casacoffeeroasters.co.uk",
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

        The `/coffee/` page is the live WooCommerce product category listing for
        the whole-bean coffee catalogue (core espresso blends + discovery
        single-origins + the curated sample packs). We deliberately do NOT crawl
        the full product sitemap here: that includes sold-out beans, brewing
        equipment, subscriptions, courses and gifts, and would defeat the
        base-class out-of-stock diffing (products in the sitemap would always
        appear "current"). The category page is the authoritative in-stock list.

        Returns:
            List containing the coffee category URL.
        """
        return ["https://casacoffeeroasters.co.uk/coffee/"]

    def _get_excluded_url_patterns(self) -> list[str]:
        """Drop the generic ``discovery`` exclusion for this roaster.

        The base pattern list uses ``"discovery"`` to skip "Discovery"
        subscription boxes on other roasters. Casa's Discovery products are a
        rotating single-origin coffee range whose curated **Sample Pack
        Discovery Range** (a tasting kit) must be extracted and flagged
        ``is_tasting_kit``/``requires_review``, not silently dropped. Removing
        ``"discovery"`` here lets both the single-origin Discovery coffees and
        the Discovery sample pack flow through to the admin review queue.
        """
        return [p for p in super()._get_excluded_url_patterns() if p != "discovery"]

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
        """Extract product URLs from the WooCommerce category page.

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

            # WooCommerce category pagination (e.g. `/coffee/page/2/`).
            next_el = soup.select_one("a.next.page-numbers, a.next")
            next_href = next_el.get("href") if next_el else None
            if not isinstance(next_href, str):
                break
            page_url = self.resolve_url(next_href)
            if "page/" not in page_url:
                break
            pages_fetched += 1

        # Deduplicate while preserving order
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
