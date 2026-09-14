"""Impossible Coffees scraper (WordPress.com showcase site, AI-powered extraction).

Impossible Coffees is a limited-edition rare-coffee project by Delta Coffee
House Experience (Delta Cafés / Grupo Nabeiro) in Portugal. The site at
impossiblecoffees.com is a WordPress.com (Jetpack) showcase with one page per
coffee — at capture: /cafe-amboim/ (Angola), /cafe-catoninho/ (São Tomé and
Príncipe), /cafe-colombia/ (Colombia), /cafe-dos-acores/ (Azores, Portugal)
and /cafe-toki/ (Thailand).

The pages are storytelling showcases, not storefronts: they carry no prices,
weights or tasting-note tables (the only € figures are fundraising counters
such as "Valor angariado ... 23078.84 €" on the Amboim page), and the
"COMPRAR" buttons link out to the external shop at
shop.deltacoffeehouse.com. The WordPress pages are therefore the product
source for discovery and description extraction, and prices are intentionally
never recorded.
"""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="impossible-coffees",
    display_name="Impossible Coffees",
    roaster_name="Impossible Coffees",
    website="https://impossiblecoffees.com",
    description="Limited-edition rare-coffee project by Delta Coffee House Experience (Delta Cafés / Grupo "
    "Nabeiro) in Portugal; one WordPress showcase page per coffee, sold via shop.deltacoffeehouse.com.",
    requires_api_key=True,
    currency="EUR",  # Portuguese project; the external shop prices in EUR
    country="Portugal",
    status="available",
)
class ImpossibleCoffeesScraper(BaseScraper):
    """Scraper for Impossible Coffees (impossiblecoffees.com) with AI-powered extraction."""

    # Product pages live at the site root: /cafe-<slug>/ (one page per coffee).
    PRODUCT_PATH_PATTERN = "/cafe-"

    def __init__(self, api_key: str | None = None):
        """Initialize Impossible Coffees scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Impossible Coffees",
            base_url="https://impossiblecoffees.com",
            rate_limit_delay=2.0,  # WordPress.com rate-limits aggressively; be respectful
            max_retries=3,
            timeout=30.0,
        )
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        The "Os Cafés" page is the showcase's coffee listing and links to all
        five per-coffee pages (the WordPress.com homepage shows the same set
        but is a landing page rather than a listing).
        """
        return ["https://impossiblecoffees.com/os-cafes/"]

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
            use_playwright=False,  # Static server-rendered WordPress.com pages
            use_optimized_mode=False,
            translate_to_english=True,  # Site content is in Portuguese
        )

    def _narrow_product_soup(self, soup, url: str):
        """Narrow a product page soup to its ``<main id="main">`` container.

        The WordPress.com Varia theme wraps the coffee story in a single
        ``<main id="main">`` element; the surrounding document is nav, styles
        and Jetpack boilerplate that only wastes extractor tokens. Listing
        pages (``/os-cafes/``) and any page without the container are returned
        unchanged.
        """
        if self.PRODUCT_PATH_PATTERN not in url.lower():
            return soup
        mains = soup.select("main#main")
        if len(mains) == 1:
            return mains[0]
        return soup

    async def fetch_page(self, url: str, retries: int = 0, use_playwright: bool = False):
        """Fetch a page, narrowing product pages to their main content container."""
        soup = await super().fetch_page(url, retries=retries, use_playwright=use_playwright)
        if soup is None:
            return None
        return self._narrow_product_soup(soup, url)

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean:
        """Pin the currency to EUR and strip any extracted prices.

        The showcase pages publish no product prices at all — the only €
        figures on them are fundraising counters ("Valor angariado ... €").
        Any price the AI extracts therefore cannot be a real product price
        and must be dropped rather than stored. The external
        shop.deltacoffeehouse.com shop prices in EUR.
        """
        bean.currency = "EUR"
        if bean.price_options or bean.price is not None:
            logger.debug(f"Dropping non-price € figure(s) extracted from a showcase page: {bean.url}")
            bean.price_options = []
            bean.price = None
        return bean

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract the per-coffee page URLs from the "Os Cafés" listing page.

        Args:
            store_url: URL of the listing page

        Returns:
            List of product URLs (one per showcase page)
        """
        # Sold-out detection: none — the WordPress.com showcase pages carry no
        # stock markers; the COMPRAR buttons link out to the external shop,
        # which is not scraped by this scraper.
        soup = await self.fetch_page(store_url, use_playwright=False)
        if not soup:
            return []

        product_urls: list[str] = []
        for a in soup.select("a[href]"):
            href = a.get("href")
            if not href or not isinstance(href, str):
                continue
            full_url = self.resolve_url(href)
            if self.is_coffee_product_url(full_url, required_path_patterns=[self.PRODUCT_PATH_PATTERN]):
                product_urls.append(full_url)

        unique_urls = list(dict.fromkeys(product_urls))
        logger.info(f"Found {len(unique_urls)} coffee page URLs from {store_url}")
        return unique_urls
