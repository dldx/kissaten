"""Cafe Domestique scraper implementation with AI-powered extraction.

Cafe Domestique is a US coffee bar / roastery hosted on Big Cartel
(cafedomestique.bigcartel.com). Big Cartel storefronts are plain server-rendered
HTML: the ``/products`` listing page carries one ``a.product-list-link`` per
product inside a ``div.product-list-thumb`` card, with a ``sold`` class on the
card when the product is sold out. Product detail pages expose clean
``og:price:amount`` / ``og:price:currency`` / ``og:availability`` meta tags and
their whole product UI lives inside the ``<main>`` element.
"""

import logging

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="cafe-domestique",
    display_name="Cafe Domestique",
    roaster_name="Cafe Domestique",
    website="https://cafedomestique.bigcartel.com",
    description=("Cafe Domestique is a specialty coffee bar and roastery in Savannah, Georgia, hosted on Big Cartel."),
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class CafeDomestiqueScraper(BaseScraper):
    """Scraper for Cafe Domestique (Big Cartel storefront) with AI extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Cafe Domestique scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Cafe Domestique",
            base_url="https://cafedomestique.bigcartel.com",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get the Big Cartel products listing URL."""
        return ["https://cafedomestique.bigcartel.com/products"]

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

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page and narrow product detail pages to the ``<main>`` container.

        Big Cartel product pages embed the whole product UI inside ``<main>``
        (~8 KB of a ~290 KB page). Narrowing to it strips the theme nav, footer
        and script blobs before the HTML reaches the AI extractor.

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
            # Only narrow product detail pages, leave listing pages untouched
            if "/product/" not in (url or ""):
                return soup
            if soup is None:
                return None
            main_el = soup.select("main")
            if len(main_el) == 1:
                logger.debug(f"Narrowed soup to <main> for {url}")
                return main_el[0]
            logger.warning(f"Expected 1 <main> for {url}, found {len(main_el)}")
            return soup
        except Exception as e:
            logger.error(f"Error fetching page {url if 'url' in dir() else '?'}: {e}")
            return None

    # Sold-out detection: Big Cartel class detection on the product card. Each
    # listing card is a div.product-list-thumb whose class list gains "sold"
    # when the product is sold out (its card text also reads "Sold out" /
    # "Coming soon"). We check the card classes and text before applying
    # is_coffee_product_url filtering, so excluded products don't leak past
    # the stock check.
    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract in-stock product URLs from the Big Cartel listing page.

        Args:
            store_url: URL of the /products listing page

        Returns:
            List of in-stock product URLs
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        product_urls: list[str] = []
        seen: set[str] = set()

        for link in soup.select("a.product-list-link[href]"):
            href = link.get("href")
            if not href or not isinstance(href, str):
                continue

            # Skip sold-out products before URL-pattern filtering: the card
            # ancestor (div.product-list-thumb) carries a "sold" class, and the
            # card text reads "Sold out" / "Coming soon" for unavailable items.
            card = link.find_parent("div", class_="product-list-thumb") or link.find_parent("li")
            card_text = card.get_text(" ", strip=True) if card else link.get_text(" ", strip=True)
            card_classes = " ".join(card.get("class") or []) if card else ""
            if "sold" in card_classes.split() or any(marker in card_text for marker in ("Sold out", "Coming soon")):
                logger.debug(f"Skipping sold-out product: {href}")
                continue

            full_url = self.resolve_url(href.split("?")[0].split("#")[0])
            if full_url in seen:
                continue
            seen.add(full_url)
            product_urls.append(full_url)

        # Exclude genuine classes/experiences (coffee roasting experience, latte
        # art class) — they are workshops, not coffee. The Fermentation Project
        # tasting kit (pre-order-fermentation-project-tasting-kit-...) is NOT
        # excluded: it is extracted and flagged as a tasting kit downstream.
        coffee_urls = [
            url for url in product_urls if self.is_coffee_product_url(url, required_path_patterns=["/product/"])
        ]
        logger.info(f"Found {len(coffee_urls)} in-stock product URLs from {store_url}")
        return coffee_urls

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Force the currency to USD as a final guard.

        Big Cartel emits og:price:currency, but pin USD in case the meta tag is
        missing or the base detection is confused.

        Args:
            bean: Extracted CoffeeBean object

        Returns:
            The bean with currency forced to USD
        """
        bean.currency = "USD"
        for option in bean.price_options or []:
            option.currency = "USD"
        return bean
