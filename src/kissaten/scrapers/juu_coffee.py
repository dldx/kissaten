"""Juu Coffee scraper implementation (WordPress/Elementor brochure catalog)."""

import logging
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="juu-coffee",
    display_name="Juu Coffee",
    roaster_name="Juu Coffee",
    website="https://juu.co.ke",
    description="Kenyan coffee processing company based in Nairobi offering Kenyan Arabica, "
    "Robusta, Excelsa and Liberica beans; orders are handled via contact/WhatsApp "
    "rather than an online cart, and prices are displayed in USD.",
    requires_api_key=True,
    currency="USD",
    country="Kenya",
    status="available",
)
class JuuCoffeeScraper(BaseScraper):
    """Scraper for Juu Coffee (juu.co.ke).

    The site is a WordPress + Elementor brochure site, not a real e-commerce
    store: there is no WooCommerce product catalog, no `/shop` or `/product/`
    pages, and every "order now" button links to `#`. The entire catalog is a
    single static page at `/products/` with four product cards (name in an
    ``h4`` heading, price in a following ``h5`` heading like "$9.75", and a
    pack-shot image).

    Because there are no per-product detail pages, we:

    1. Parse the product cards from `/products/` and synthesize a stable
       per-product URL using a fragment (`https://juu.co.ke/products/#<slug>`).
    2. Cache each card's HTML and serve it from `fetch_page` so the AI
       extraction runs per product without refetching the (aggressively
       rate-limited, Imunify360-protected) listing page.
    """

    # Juu's Elementor card layout: each product lives in a 25%-width inner
    # column containing an h4 (name) followed by an h5 (price like "$9.75").
    CARD_SELECTOR = "div.elementor-inner-column"

    def __init__(self, api_key: str | None = None):
        """Initialize Juu Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Juu Coffee",
            base_url="https://juu.co.ke",
            # The site sits behind Imunify360 and rate-limits hard (429s even
            # with ~10s between requests), so use a generous delay and retries.
            rate_limit_delay=10.0,
            max_retries=4,
            timeout=60.0,
        )
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

        # Synthetic product URL -> card HTML (populated during listing parse).
        self._product_cards: dict[str, str] = {}

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the single static catalog page.
        """
        return ["https://juu.co.ke/products/"]

    def _parse_price(self, text: str) -> float | None:
        """Parse a price like "$9.75" into a float.

        Args:
            text: Raw heading text

        Returns:
            Price as float, or None if no price found.
        """
        match = re.search(r"[\$€£]\s*(\d+(?:[.,]\d{1,2})?)", text)
        if not match:
            return None
        try:
            return float(match.group(1).replace(",", "."))
        except ValueError:
            return None

    @staticmethod
    def _slugify(name: str) -> str:
        """Convert a product name into a URL-fragment-friendly slug."""
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        return slug or "unknown"

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract synthetic product URLs from the static catalog page.

        # Sold-out detection: none — the catalog page has no stock UI at all
        # (no "out of stock"/"sold out" markers; products are ordered via
        # contact buttons), so every listed card is treated as in stock.

        Args:
            store_url: The catalog page URL

        Returns:
            List of synthetic per-product URLs.
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            # Record the failure so out-of-stock updates are suppressed for
            # this session (empty catalog from a failed fetch is not
            # trustworthy — see BaseScraper.create_diffjson_stock_updates).
            if store_url not in self._failed_listing_urls:
                self._failed_listing_urls.append(store_url)
                logger.warning(f"Failed to fetch catalog page {store_url}; suppressing stock updates this session")
            return []

        found_urls: list[str] = []
        for column in soup.select(self.CARD_SELECTOR):
            name_el = column.select_one("h4.elementor-heading-title")
            price_el = column.select_one("h5.elementor-heading-title")
            if not name_el or not price_el:
                continue

            name = name_el.get_text(" ", strip=True)
            price_text = price_el.get_text(" ", strip=True)
            price = self._parse_price(price_text)
            if not name or price is None:
                continue

            slug = self._slugify(name)
            product_url = f"{store_url.rstrip('/')}/#{slug}"

            # Cache the card HTML so fetch_page can serve it per product
            # without re-fetching the rate-limited listing page.
            self._product_cards[product_url] = str(column)

            # The card also carries the pack-shot image; keep it alongside
            # the URL so the AI extractor can reference it via the card HTML.
            img = column.select_one("img")
            if img and img.get("src"):
                img["src"] = urljoin(store_url, img["src"])

            if self.is_coffee_product_name(name):
                found_urls.append(product_url)
                logger.debug(f"Found product card: {name} at {price_text}")
            else:
                logger.debug(f"Skipping non-coffee card: {name}")

        logger.info(f"Parsed {len(found_urls)} product cards from {store_url}")
        return self.deduplicate_urls(found_urls)

    async def fetch_page(self, url: str, retries: int = 0, use_playwright: bool = False) -> BeautifulSoup | None:
        """Serve cached card HTML for synthetic product URLs; fetch otherwise.

        The synthetic fragment URLs (`/products/#<slug>`) have no real pages,
        so we return the card HTML captured during listing parsing instead of
        hitting the network again (the site rate-limits aggressively).

        Args:
            url: URL to fetch
            retries: Number of retries attempted
            use_playwright: Whether to use Playwright

        Returns:
            BeautifulSoup object or None if failed.
        """
        if url in self._product_cards:
            logger.debug(f"Serving cached card HTML for {url}")
            return BeautifulSoup(self._product_cards[url], "lxml")
        return await super().fetch_page(url, retries=retries, use_playwright=use_playwright)

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using AI extraction on the cached card HTML.

        Args:
            product_urls: List of synthetic product URLs

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

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        # The site displays prices with a "$" sign and there is no currency
        # metadata anywhere on the static page, so detection never fires and
        # the default would fall back to the registry default. Juu prices in
        # USD — force it as a final guard.
        bean.currency = "USD"
        return bean
