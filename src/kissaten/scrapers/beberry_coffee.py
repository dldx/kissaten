"""BeBerry Coffee scraper implementation with AI-powered extraction.

BeBerry Coffee (beberrycoffee.cz) is a Prague, Czechia specialty roastery on
WordPress/WooCommerce. The whole-bean catalogue lives under the ``kava``
("coffee") category ``/categories/kava/``; product detail pages use
``/product/<slug>/`` URLs. Product pages are in Czech, so the AI extractor
runs with ``translate_to_english=True``.

The ``kava`` category also lists two coffee-cherry/blossom teas
(``cascara-coffee-cherry-tea`` and ``kavovy-kvet``). They are genuine
non-bean items (cascara is coffee cherry tea, "kávovníkový květ" is coffee
blossom tea — both ``product_cat-jine`` = "other"), so they are excluded the
same way other scrapers exclude cascara ("coffee cherry tea, not beans").
"""

import logging

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="beberry-coffee",
    display_name="BeBerry Coffee",
    roaster_name="BeBerry Coffee",
    website="https://www.beberrycoffee.cz",
    description="Prague specialty coffee roastery (Pražská pražírna specializované kávy) "
    "selling direct-trade single origins, espresso and filter coffees via a Czech "
    "WooCommerce storefront, priced in CZK",
    requires_api_key=True,
    currency="CZK",
    country="Czechia",
    status="available",
)
class BeBerryCoffeeScraper(BaseScraper):
    """Scraper for BeBerry Coffee (beberrycoffee.cz) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize the BeBerry Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="BeBerry Coffee",
            base_url="https://www.beberrycoffee.cz",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page and narrow WooCommerce product detail pages to ``div.product``.

        BeBerry's WooCommerce product pages embed all useful content (title,
        price, description, tasting notes) inside ``div.product``. Narrowing
        the soup to that container strips nav, footer, cookie-consent and JS
        blobs before the HTML reaches the AI extractor, keeping token usage low.
        Listing/category pages are left untouched.
        """
        try:
            soup = await super().fetch_page(*args, **kwargs)
            url = kwargs.get("url")
            if not url and len(args) > 0:
                url = args[0]
            # Only narrow product detail pages ("/product/<slug>/"),
            # leave the category page ("/categories/kava/") untouched.
            if "/product/" not in (url or ""):
                return soup
            if soup is None:
                return None
            product_el = soup.select("div.product")
            if len(product_el) == 1:
                logger.debug(f"Narrowed soup to div.product for {url}")
                return product_el[0]
            logger.warning(f"Expected 1 div.product for {url}, found {len(product_el)}")
            return soup
        except Exception as e:
            logger.error(f"Error fetching page {kwargs.get('url', args[0] if args else '?')}: {e}")
            return None

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape (the Kava / Coffee category)."""
        return ["https://www.beberrycoffee.cz/categories/kava/"]

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
            translate_to_english=True,  # Czech product pages
        )

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        # WooCommerce pages carry no og:price:currency meta tag, so the base
        # currency detection never fires and default_currency silently falls
        # back to the registry default. BeBerry prices in CZK; force it.
        bean.currency = "CZK"
        return bean

    # Sold-out detection: WooCommerce class detection on the product card.
    # BeBerry (WooCommerce) marks sold-out products by swapping the
    # ``instock``/``outofstock`` class on the ``li.product`` card. Text
    # detection is NOT usable here: every variable product card contains a
    # disabled "Dočasně vyprodáno" (temporarily sold out) add-to-cart button
    # even when the product is in stock, so a substring check would
    # false-positive on the whole catalogue. Skip any card whose class list
    # contains ``outofstock`` before applying is_coffee_product_url filtering.
    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract in-stock coffee product URLs from the Kava category page.

        Args:
            store_url: URL of the store/category page

        Returns:
            List of in-stock coffee product URLs
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        # Non-bean products that can appear in the kava category: cascara
        # (coffee cherry tea) and "kávovníkový květ" (coffee blossom tea).
        excluded_products = [
            "cascara",  # coffee cherry tea, not beans
            "kavovy-kvet",  # coffee blossom tea, not beans
            "filtry",  # Czech for filters
            "subscription",
            "gift-card",
            "gift",
            "merch",
            "merchandise",
            "equipment",
            "grinder",
        ]

        product_urls: list[str] = []
        seen: set[str] = set()

        cards = soup.select("li.product")
        for card in cards:
            classes = " ".join(card.get("class") or [])
            # Skip sold-out products (WooCommerce 'outofstock' on the card).
            if any(token in classes for token in ("outofstock", "sold-out", "oos")):
                continue
            link = card.select_one('a[href*="/product/"]')
            if not link:
                continue
            href = link.get("href")
            if not href or not isinstance(href, str):
                continue
            full_url = self.resolve_url(href)
            url_lower = full_url.lower()
            # Drop the non-bean teas/filters before the generic coffee filter.
            if any(excluded in url_lower for excluded in excluded_products):
                logger.debug(f"Excluding non-coffee product URL: {full_url}")
                continue
            # Apply coffee filtering before adding so any other non-coffee
            # products (merch, equipment) are kept out.
            if self.is_coffee_product_url(full_url, required_path_patterns=["/product/"]):
                if full_url not in seen:
                    seen.add(full_url)
                    product_urls.append(full_url)

        logger.info(f"Found {len(product_urls)} in-stock coffee product URLs from {store_url}")
        return product_urls
