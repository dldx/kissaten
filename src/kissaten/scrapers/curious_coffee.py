"""Curious Coffee scraper implementation with AI-powered extraction (Wix storefront)."""

import logging

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="curious-coffee",
    display_name="Curious Coffee",
    roaster_name="Curious Coffee",
    website="https://www.curious-coffee.com",
    description="Micro-roastery and coffee education studio based in Ann Arbor, Michigan, "
    "sourcing exceptional green coffees and roasting them light to make them shine.",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class CuriousCoffeeScraper(BaseScraper):
    """Scraper for Curious Coffee (curious-coffee.com) with AI-powered extraction.

    The site is a Wix storefront (verified via ``<meta name="generator"
    content="Wix.com Website Builder">``), so this follows the greytone_coffee.py
    model: static server-rendered listing pages with ``div[data-hook="product-item-root"]``
    cards, product detail pages narrowed to ``div[data-hook="product-page"]``.

    The Wix "all-products" category only renders 15 product cards per request;
    the rest are loaded via JS. Static pagination via ``?page=N`` works, so the
    store extraction loops pages until no new cards appear.
    """

    # Maximum Wix category pages to walk (?page=N). The catalogue currently
    # fits in 3 pages of 15 cards; the loop stops earlier when a page yields
    # no new cards.
    _max_listing_pages = 10

    # Non-coffee slugs to exclude (equipment/merch/subscriptions shown in the
    # Wix store). Clothing (t-shirts/sweatshirts/tote) and subscriptions are
    # already excluded by the base class patterns.
    _excluded_url_slugs = [
        "coffee-club",  # Curious Coffee Club subscription
        "monthly-coffee-subscription",
        "mypressi-twist",  # portable espresso maker
        "fellow-aiden-precision-coffee-maker",  # brewer
        "trendglas-server",  # glass server
        "lotus-coffee-water-drops",  # water mineral drops
        "little-cup",  # Aoomi Lovely Little Cup (drinkware)
    ]

    def __init__(self, api_key: str | None = None):
        """Initialize Curious Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Curious Coffee",
            base_url="https://www.curious-coffee.com",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the Wix all-products category URL.
        """
        return ["https://www.curious-coffee.com/category/all-products"]

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page and narrow product detail pages to the Wix product container.

        Wix product detail pages embed all useful content inside
        ``div[data-hook="product-page"]``. Narrowing the soup to that container
        strips nav, footer, JSON blobs, and unrelated markup before the HTML is
        sent to the AI extractor, which dramatically reduces token noise.

        Args:
            *args: Positional arguments forwarded to the base fetch_page.
            **kwargs: Keyword arguments forwarded to the base fetch_page.

        Returns:
            BeautifulSoup object (narrowed for product pages) or None if fetch failed.
        """
        soup = await super().fetch_page(*args, **kwargs)
        url = kwargs.get("url")
        if not url and len(args) > 0:
            url = args[0]
        # Only narrow product detail pages, leave listing/category pages untouched
        if not url or "/product-page/" not in url:
            return soup
        if soup is None:
            return None
        product_el = soup.select("div[data-hook='product-page']")
        if len(product_el) == 1:
            logger.debug(f"Narrowed soup to div[data-hook='product-page'] for {url}")
            return product_el[0]
        logger.warning(f"Expected 1 div[data-hook='product-page'] for {url}, found {len(product_el)}")
        return soup

    # Sold-out detection: Wix text detection on the product-item-root card.
    # Sold-out products show "Out of stock" / "Sold out" / "Unavailable" button
    # text inside their card container. We check each card's own text (never a
    # whole-page search — those markers also appear inside embedded JSON/JS)
    # and skip sold-out cards BEFORE applying is_coffee_product_url filtering,
    # so excluded products don't leak past the stock check.
    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from the Wix category listing, filtering sold-out items.

        Walks the static ``?page=N`` pagination until a page yields no new
        product cards (Wix renders 15 cards per page server-side).

        Args:
            store_url: URL of the Wix category page

        Returns:
            List of in-stock product URLs
        """
        product_urls: list[str] = []
        seen: set[str] = set()

        for page_num in range(1, self._max_listing_pages + 1):
            page_url = store_url if page_num == 1 else f"{store_url}?page={page_num}"
            soup = await self.fetch_page(page_url)
            if soup is None:
                logger.warning(f"Failed to fetch listing page: {page_url}")
                break

            items = soup.select('[data-hook="product-item-root"]')
            if not items:
                logger.debug(f"No product cards on listing page {page_num}, stopping pagination")
                break

            new_cards = 0
            for item in items:
                link = item.select_one('a[href*="/product-page/"]')
                if not link:
                    continue
                href = link.get("href")
                if not href or not isinstance(href, str):
                    continue

                # Strip query string and fragment; resolve to absolute URL
                full_url = self.resolve_url(href.split("?")[0].split("#")[0])

                # Skip sold-out products before URL-pattern filtering
                item_text = item.get_text(" ", strip=True).lower()
                if any(marker in item_text for marker in ("out of stock", "sold out", "unavailable")):
                    logger.debug(f"Skipping sold-out product: {full_url}")
                    continue

                if full_url in seen:
                    continue
                seen.add(full_url)
                product_urls.append(full_url)
                new_cards += 1

            logger.debug(f"Listing page {page_num}: {new_cards} new product cards")

            if new_cards == 0:
                # Page repeated products we already have (or Wix looped back to
                # page 1) — catalogue exhausted.
                break

        # Exclude non-coffee products (equipment, merch, subscriptions)
        coffee_urls = []
        for url in product_urls:
            if not self.is_coffee_product_url(url, required_path_patterns=["/product-page/"]):
                continue
            url_lower = url.lower()
            if any(slug in url_lower for slug in self._excluded_url_slugs):
                logger.debug(f"Excluding non-coffee product URL: {url}")
                continue
            coffee_urls.append(url)

        logger.info(f"Found {len(coffee_urls)} in-stock coffee product URLs from {store_url}")
        return coffee_urls

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
            translate_to_english=False,
        )

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Pin USD as the store currency.

        Wix product pages carry no ``og:price:currency`` meta tag, so the base
        class's currency detection never fires and the registry default could
        silently fall back to GBP. Pin it here as a final guard.
        """
        bean.currency = "USD"
        return bean
