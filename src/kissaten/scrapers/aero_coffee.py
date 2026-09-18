"""Aero Coffee Roasters scraper implementation with AI-powered extraction.

Platform: Wix storefront (``<meta name="generator" content="Wix.com Website Builder"/>``).
Listing pages expose ``[data-hook="product-item-root"]`` cards whose "ADD TO CART"
button turns into "Out of Stock" for unavailable products; product detail pages wrap
everything in ``div[data-hook="product-page"]``. Model scraper used: ``greytone_coffee.py``
(Wix, no Playwright required — httpx serves the product markup).
"""

import logging

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="aero-coffee",
    display_name="Aero Coffee Roasters",
    roaster_name="Aero Coffee Roasters",
    website="https://www.aerocoffeeroasters.com",
    description=(
        "United States specialty coffee roaster offering single-origin microlots and The Fermentation Project sets."
    ),
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class AeroCoffeeScraper(BaseScraper):
    """Scraper for Aero Coffee Roasters (aerocoffeeroasters.com) with AI extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Aero Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Aero Coffee Roasters",
            base_url="https://www.aerocoffeeroasters.com",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get the all-products shop URL."""
        return ["https://www.aerocoffeeroasters.com/shop"]

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page and narrow Wix product detail pages to the product container.

        Wix product detail pages embed all useful content inside
        ``div[data-hook="product-page"]``. Narrowing the soup to that container strips
        nav, footer, JSON blobs and unrelated markup before the HTML reaches the AI
        extractor, which drastically reduces token noise.
        """
        try:
            soup = await super().fetch_page(*args, **kwargs)
            url = kwargs.get("url")
            if not url and len(args) > 0:
                url = args[0]
            if "/product-page/" not in (url or ""):
                return soup
            if soup is None:
                return None
            product_el = soup.select("div[data-hook='product-page']")
            if len(product_el) == 1:
                logger.debug(f"Narrowed soup to div[data-hook='product-page'] for {url}")
                return product_el[0]
            logger.warning(f"Expected 1 div[data-hook='product-page'] for {url}, found {len(product_el)}")
            return soup
        except Exception as e:
            logger.error(f"Error fetching page {args[0] if args else kwargs.get('url')}: {e}")
            return None

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract in-stock product URLs from the Wix shop listing.

        # Sold-out detection: Wix card-level text detection on the
        # ``[data-hook="product-item-root"]`` container. Sold-out Wix products render
        # "Out of Stock" / "Sold out" / "Unavailable" in place of "ADD TO CART". The
        # check runs on the card text (never the whole page) and before
        # ``is_coffee_product_url`` filtering.
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        product_urls: list[str] = []
        seen: set[str] = set()

        for item in soup.select('[data-hook="product-item-root"]'):
            link = item.select_one('a[href*="/product-page/"]')
            if not link or not isinstance(link.get("href"), str):
                continue

            full_url = self.resolve_url(link["href"].split("?")[0].split("#")[0])

            item_text = " ".join(item.get_text(" ", strip=True).split())
            if any(marker in item_text for marker in ("Out of Stock", "Sold out", "Sold Out", "Unavailable")):
                logger.debug(f"Skipping sold-out product: {full_url}")
                continue

            if not self.is_coffee_product_url(full_url, required_path_patterns=["/product-page/"]):
                continue

            if full_url not in seen:
                seen.add(full_url)
                product_urls.append(full_url)

        # Exclude non-coffee products (accessories, subscriptions, gift cards).
        excluded = ["subscription", "gift-card", "giftcard", "equipment", "accessor"]
        coffee_urls = [url for url in product_urls if not any(ex in url.lower() for ex in excluded)]

        logger.info(
            f"Found {len(coffee_urls)} in-stock coffee product URLs out of {len(product_urls)} from {store_url}"
        )
        return coffee_urls

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction."""
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
        """Pin USD — the registry default-currency lookup falls back to GBP for hyphenated names."""
        bean.currency = "USD"
        return bean
