"""Gringo Nordic scraper implementation with AI extraction.

Gringo Nordic (gringonordic.se) is a Swedish specialty coffee roaster in
Gothenburg running a WordPress/WooCommerce storefront (Elementor + JetWooBuilder
archive cards).

Discovery notes (2026-09, curl-first):
- Platform: WooCommerce. ``products.json`` 404s (not Shopify).
- The whole coffee catalogue lives under ``/product-category/kaffe/`` (with
  espresso, single-origin, bryggkaffe, decaf and prenumeration subcategories);
  tea and accessories live under sibling categories that we do not crawl.
- Product URLs are ``/product/<slug>/``; pagination uses ``/page/N/`` and the
  last page (currently 5 products on page 2) returns 404 past the end, which
  stops the pagination walk.
- WooCommerce stock classes are preserved on the JetWooBuilder cards:
  ``li.product.instock`` / ``li.product.outofstock``, and subscription
  products carry ``product-type-simple-subscription`` /
  ``product-type-variable-subscription`` classes. The variable-subscription
  "single-origin" product (slug ``/product/single-origin/``) shows that slugs
  alone cannot separate subscriptions from coffee, so the card-level class
  check is required.
"""

import logging

from bs4 import BeautifulSoup

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)

STORE_URL = "https://www.gringonordic.se/product-category/kaffe/"

# Swedish non-coffee items that may appear inside the kaffe category
# (prenumeration = subscription, presentkort = gift card, mugg/kopp = mug/cup).
EXCLUDED_URL_PATTERNS = [
    "prenumeration",
    "presentkort",
    "mugg",
    "kopp",
    "beanie",
    "tshirt",
]


@register_scraper(
    name="gringo-nordic",
    display_name="Gringo Nordic",
    roaster_name="Gringo Nordic",
    website="https://www.gringonordic.se",
    description=(
        "Swedish specialty coffee roaster in Gothenburg roasting single-origin "
        "espresso and filter coffees with a Nordic profile."
    ),
    requires_api_key=True,
    currency="SEK",
    country="Sweden",
    status="experimental",
)
class GringoNordicScraper(BaseScraper):
    """Scraper for Gringo Nordic (gringonordic.se) — a WooCommerce storefront.

    Model: ``koppi.py`` (server-rendered listing + AI extraction) with the
    WooCommerce card-class sold-out pattern from ``the_underdog.py``.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Gringo Nordic scraper."""
        super().__init__(
            roaster_name="Gringo Nordic",
            base_url="https://www.gringonordic.se",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Return the coffee category URL (pagination is followed dynamically)."""
        return [STORE_URL]

    @staticmethod
    def _page_url(store_url: str, page_number: int) -> str:
        """Build the listing URL for a given 1-based WooCommerce page number."""
        if page_number == 1:
            return store_url
        return f"{store_url.rstrip('/')}/page/{page_number}/"

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract coffee product URLs from the WooCommerce kaffe category.

        Follows ``/page/N/`` pagination until a page fails to fetch or yields
        no product links.

        Args:
            store_url: Category page URL

        Returns:
            List of in-stock coffee product URLs
        """
        product_urls: list[str] = []
        page_number = 1
        while True:
            soup = await self.fetch_page(self._page_url(store_url, page_number))
            if not soup:
                # Fetch failed (404 past the last page, network error, ...).
                # Stop the walk; scrape() records the store URL as failed so
                # out-of-stock updates are suppressed for this session.
                break

            page_urls = self._extract_product_urls_from_listing_soup(soup)
            logger.info(f"Found {len(page_urls)} product URLs on {self._page_url(store_url, page_number)}")

            if not page_urls and page_number > 1:
                # Empty page beyond the last paginated one — stop walking.
                break

            product_urls.extend(page_urls)
            page_number += 1

            if page_number > 50:  # Safety bound against pagination loops
                break

        # De-duplicate while preserving order
        product_urls = list(dict.fromkeys(product_urls))

        coffee_urls = [
            url
            for url in product_urls
            if self.is_coffee_product_url(url, required_path_patterns=["/product/"])
            and not any(ex in url.lower() for ex in EXCLUDED_URL_PATTERNS)
        ]
        logger.info(
            f"Found {len(coffee_urls)} coffee product URLs out of {len(product_urls)} total products from {store_url}"
        )
        return coffee_urls

    def _extract_product_urls_from_listing_soup(self, soup: BeautifulSoup) -> list[str]:
        """Extract in-stock, non-subscription product URLs from one listing page.

        Args:
            soup: BeautifulSoup of a WooCommerce category page

        Returns:
            List of product URLs found on the page
        """
        # Sold-out detection: WooCommerce stock class on the li.product card
        # (JetWooBuilder archive items keep the WooCommerce classes). Cards
        # with "outofstock" are skipped, as are subscription products detected
        # via their "product-type-*-subscription" classes.
        urls = []
        for card in soup.select("li.product"):
            classes = card.get("class", [])
            if "outofstock" in classes:
                continue
            if any("subscription" in c for c in classes):
                continue

            link = card.select_one("a[href*='/product/']")
            if link and link.get("href"):
                urls.append(self.resolve_url(link["href"]))
        return urls

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
            translate_to_english=True,  # Swedish site — translate to English
        )

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Pin SEK as the store currency (guards against the GBP fallback)."""
        bean.currency = "SEK"
        return bean
