"""La Tostadora scraper implementation with AI-powered extraction (Wix storefront).

La Tostadora (latostadora.coffee) is a micro-roastery & coffee shop in East
London (Railway Arch, 267 Poyser Street, London E2 9RF) running a Wix
storefront. The whole-bean catalogue lives on the single ``/coffees`` listing
page. Product cards are ``div[data-hook="product-item-root"]`` containers whose
links point to ``/product-page/<slug>``. Product detail pages embed all useful
content inside ``div[data-hook="product-page"]``.
"""

import logging

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="la-tostadora",
    display_name="La Tostadora",
    roaster_name="La Tostadora",
    website="https://www.latostadora.coffee",
    description="Micro-roastery & coffee shop at Railway Arch, 267 Poyser Street, London E2 9RF.",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class LaTostadoraScraper(BaseScraper):
    """Scraper for La Tostadora (latostadora.coffee) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize La Tostadora scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="La Tostadora",
            base_url="https://www.latostadora.coffee",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

        # The Wix storefront exposes no og:price:currency meta tag, so the base
        # currency detection never fires and default_currency falls back to the
        # registry default. La Tostadora prices in GBP; pin it up front so every
        # product page uses the correct currency without re-parsing.
        self.store_currency = "GBP"
        self._currency_detected = True

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape (the single /coffees whole-bean listing).

        Returns:
            List containing the coffee collection URL.
        """
        return ["https://www.latostadora.coffee/coffees"]

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page and narrow product detail pages to the Wix product container.

        Wix product detail pages embed all useful content inside
        ``div[data-hook="product-page"]``. Narrowing the soup to that container
        strips nav, footer, JSON blobs, and unrelated markup before the HTML is
        sent to the AI extractor, keeping token usage low. The listing page
        (``/coffees``) is left untouched.

        Args:
            *args: Positional arguments forwarded to the base fetch_page.
            **kwargs: Keyword arguments forwarded to the base fetch_page.

        Returns:
            BeautifulSoup object (narrowed for product pages) or None if fetch failed.
        """
        try:
            soup = await super().fetch_page(*args, **kwargs)
            url = kwargs.get("url")
            if not url and len(args) > 0:
                url = args[0]
            # Only narrow product detail pages, leave the listing page untouched
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
            logger.error(f"Error fetching page {url if 'url' in dir() else '?'}: {e}")
            return None

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        # The Wix storefront has no og:price:currency meta tag, so the base
        # currency detection never fires. La Tostadora prices in GBP; force it.
        bean.currency = "GBP"
        return bean

    async def _scrape_new_products(
        self, product_urls: list[str], use_optimized_mode: bool = False
    ) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction.

        Args:
            product_urls: List of URLs for new products
            use_optimized_mode: Whether to use optimized (visual) extraction mode

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
            use_optimized_mode=use_optimized_mode,
        )

    # Sold-out detection: Wix text detection on the product-item-root container.
    # When a Wix product is sold out, the "Add to Cart" button text becomes
    # "Unavailable" / "Sold out" / "Out of stock" inside the product-item-root
    # container. We skip any product-item-root whose text contains those markers
    # before applying is_coffee_product_url filtering, so excluded products
    # don't leak past the stock check. The base-class exclusion patterns drop
    # non-bean items (e.g. the espresso subscription); tasting kits/samplers are
    # deliberately NOT excluded here and instead flow through to be flagged
    # is_tasting_kit/requires_review by the base class.
    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract coffee product URLs from the Wix coffee listing, filtering sold-out items.

        Args:
            store_url: URL of the store/category page

        Returns:
            List of in-stock coffee product URLs
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        product_urls: list[str] = []
        seen: set[str] = set()

        for item in soup.select('[data-hook="product-item-root"]'):
            link = item.select_one('a[href*="/product-page/"]')
            if not link:
                continue
            href = link.get("href")
            if not href or not isinstance(href, str):
                continue

            # Strip query string and fragment to get the canonical product URL
            full_url = self.resolve_url(href.split("?")[0].split("#")[0])

            # Skip sold-out products before URL-pattern filtering
            item_text = item.get_text(" ", strip=True)
            if any(marker in item_text for marker in ("Unavailable", "Sold out", "Out of stock", "SOLD OUT")):
                logger.debug(f"Skipping sold-out product: {full_url}")
                continue

            # Apply standard coffee-product URL filtering (uses /product-page/ path pattern)
            if not self.is_coffee_product_url(full_url, required_path_patterns=["/product-page/"]):
                continue

            if full_url not in seen:
                seen.add(full_url)
                product_urls.append(full_url)

        logger.info(f"Found {len(product_urls)} in-stock product URLs from {store_url}")
        return product_urls
