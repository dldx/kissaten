"""Peak and Bean scraper implementation with AI extraction.

Peak and Bean is a specialty coffee roaster in Quetzaltenango, Guatemala
(verified from the site title "Peak and Beans | cafe | Quetzaltenango,
Guatemala" and GTQ pricing). Their storefront is split across two platforms:

- ``www.peakandbeans.com`` — a Wix marketing site (no product links at all)
- ``odoo.peakandbeans.com`` — the actual Odoo eCommerce shop with the catalogue

This scraper therefore targets the Odoo shop.

Discovery notes (2026-09, curl-first):
- Platform: Odoo (website_sale). Neither host serves Shopify ``products.json``.
- Product URLs are ``/en/shop/<slug>-<numeric-id>``; the listing paginates via
  ``/en/shop/page/N`` (9 pages, 188 products at discovery time; the walk stops
  on the first page that fails to fetch or yields no products).
- Prices render as "25.00 Q" (Guatemalan quetzal, GTQ); the site also offers a
  USD pricelist but GTQ is the default display currency.
- Listing cards are ``div.oe_product`` elements. No sold-out products existed
  at discovery time, so the sold-out detection below is based on Odoo's
  documented listing badges ("Out of stock" / "Agotado" text or the
  ``o_website_sale_out_of_stock`` class) — checked at the card level only.
- Product detail pages have a stable ``.o_wsale_product_page`` container
  (~12 KB of the ~140 KB page) holding the title, price, variants and images —
  ``fetch_page`` narrows to it for AI extraction token savings.
"""

import logging
import re

from bs4 import BeautifulSoup

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)

STORE_URL = "https://odoo.peakandbeans.com/en/shop"

# Odoo product URL, e.g. /en/shop/blend-h-2129 (slug ends in -<numeric id>)
PRODUCT_URL_RE = re.compile(r"/shop/[^/]+-\d+/?(?:\?.*)?$")

# Brewing equipment and drinkware sold in the shop (Fellow Aiden/Ode brewers
# and grinders, drippers, scales, ...). Product names are Spanish/Dutch mix,
# so both languages are covered. Roasted coffee slugs are things like
# blend-h-2129, bourbon-h-lavado-2123, gesha-natural-atitlan-panorama-2143.
EXCLUDED_URL_PATTERNS = [
    "aiden",  # Fellow Aiden brewer (incl. color variants)
    "ode-gen",  # Fellow Ode grinder
    "outin",  # OutIn portable grinder/espresso maker
    "sibarist",
    "cyclone",  # bottle/carafe
    "espresso-series",  # Fellow Espresso Series machine
    "timer-toddy",
    "dripper",
    "grinder",
    "molino",
    "molinillo",
    "termo",
    "vaso",
    "taza",
    "mug",
]


@register_scraper(
    name="peak-and-bean",
    display_name="Peak and Bean",
    roaster_name="Peak and Bean",
    website="https://www.peakandbeans.com",
    description=(
        "Specialty coffee roaster in Quetzaltenango, Guatemala, roasting "
        "Bourbon, Caturra, Gesha, Marsellesa and Pacamara lots from Guatemalan "
        "farms."
    ),
    requires_api_key=True,
    currency="GTQ",
    country="Guatemala",
    status="experimental",
)
class PeakAndBeanScraper(BaseScraper):
    """Scraper for Peak and Bean (odoo.peakandbeans.com) — an Odoo storefront.

    Model: ``koppi.py`` (server-rendered listing + AI extraction) with an
    Odoo-specific pagination walk, card-level sold-out text detection (the
    ``the_underdog.py`` pattern) and ``fetch_page`` narrowing to the Odoo
    product container (the ``greytone_coffee.py`` token lever).
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Peak and Bean scraper."""
        super().__init__(
            roaster_name="Peak and Bean",
            base_url="https://odoo.peakandbeans.com",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Return the Odoo shop listing URL (pagination is followed dynamically)."""
        return [STORE_URL]

    @staticmethod
    def _page_url(store_url: str, page_number: int) -> str:
        """Build the listing URL for a given 1-based Odoo page number."""
        if page_number == 1:
            return store_url
        return f"{store_url.rstrip('/')}/page/{page_number}"

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract coffee product URLs from the Odoo shop listing.

        Follows ``/page/N`` pagination until a page fails to fetch or yields
        no product links.

        Args:
            store_url: Shop listing URL

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
            if self.is_coffee_product_url(url, required_path_patterns=["/shop/"])
            and PRODUCT_URL_RE.search(url)
            and not any(ex in url.lower() for ex in EXCLUDED_URL_PATTERNS)
        ]
        logger.info(
            f"Found {len(coffee_urls)} coffee product URLs out of {len(product_urls)} total products from {store_url}"
        )
        return coffee_urls

    def _extract_product_urls_from_listing_soup(self, soup: BeautifulSoup) -> list[str]:
        """Extract in-stock product URLs from one Odoo listing page.

        Args:
            soup: BeautifulSoup of an Odoo shop page

        Returns:
            List of product URLs found on the page
        """
        # Sold-out detection: text check on each div.oe_product card for the
        # Odoo stock badges ("Out of stock" / "Agotado" / "Sold out") plus the
        # o_website_sale_out_of_stock class — card-level only, never a
        # whole-page search (Odoo templates embed those strings in JS).
        urls = []
        for card in soup.select("div.oe_product"):
            classes = " ".join(card.get("class", []))
            card_text = " ".join(card.get_text(" ", strip=True).split()).lower()
            if (
                "o_website_sale_out_of_stock" in classes
                or "out of stock" in card_text
                or "agotado" in card_text
                or "sold out" in card_text
            ):
                continue

            link = card.select_one("a.oe_product_image_link") or card.find(
                "a", href=lambda h: h and PRODUCT_URL_RE.search(h)
            )
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
            translate_to_english=True,  # Spanish product names/descriptions
        )

    async def fetch_page(self, *args, **kwargs):
        """Narrow Odoo product detail pages to the ``.o_wsale_product_page``
        container (title, price, variants, images); listing pages pass through
        untouched."""
        soup = await super().fetch_page(*args, **kwargs)
        url = kwargs.get("url") or (args[0] if args else "")
        if not PRODUCT_URL_RE.search(url):
            return soup

        return self._narrow_product_soup(soup)

    @staticmethod
    def _narrow_product_soup(soup: BeautifulSoup | None) -> BeautifulSoup | None:
        """Return only the stable Odoo product container of a detail page."""
        if soup is None:
            return None

        container = soup.select_one(".o_wsale_product_page")
        if container is not None:
            return container
        return soup

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Pin GTQ as the store currency (guards against the GBP fallback; the
        Odoo shop also exposes a USD pricelist but displays GTQ by default)."""
        bean.currency = "GTQ"
        return bean
