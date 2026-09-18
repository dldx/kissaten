"""The God Shot scraper implementation with AI-powered extraction (Odoo storefront)."""

import logging

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="the-god-shot",
    display_name="The God Shot",
    roaster_name="The God Shot",
    website="https://www.thegodshot.be",
    description=(
        "Specialty coffee roaster, bar and training centre in Brussels, Belgium, "
        "roasting tailored coffees and running brewing courses and a coffee forum."
    ),
    requires_api_key=True,
    currency="EUR",
    country="Belgium",
    status="experimental",
)
class TheGodShotScraper(BaseScraper):
    """Scraper for The God Shot (thegodshot.be) — an Odoo eCommerce storefront.

    Odoo renders everything server-side: the ``/shop/category/coffee-beans-3``
    category page lists the bean products as ``article.oe_product_cart`` cards,
    and product pages carry the details in ``#product_details``,
    ``#product_full_description`` and ``#product_specifications`` — the page
    soup is narrowed to those containers before AI extraction. Sample packs are
    kept (flagged as tasting kits downstream); subscriptions and brew gear are
    excluded.
    """

    # Product path prefix used by the coffee-beans category listing.
    _PRODUCT_PATH = "/shop/coffee-beans-3/"

    # Non-coffee URL slug substrings (brew gear in the beans category).
    _excluded_url_slugs = [
        "fellow",  # Fellow Atmos vacuum canisters
    ]

    def __init__(self, api_key: str | None = None):
        """Initialize The God Shot scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="The God Shot",
            base_url="https://www.thegodshot.be",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = None
        try:
            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
        except ValueError:
            logger.warning("Google API key not configured. AI extraction will not be available.")

    async def get_store_urls(self) -> list[str]:
        """Return the Odoo coffee-beans category listing URL."""
        return ["https://www.thegodshot.be/shop/category/coffee-beans-3"]

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
            translate_to_english=False,  # Shop renders in English by default
        )

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page and narrow product detail pages to the Odoo product containers.

        Odoo product detail pages carry the useful content in
        ``#product_details`` (name/price/variants/CTA), ``#product_full_description``
        (the long description) and ``#product_specifications``. Narrowing the
        soup to those containers strips nav, footer, cart JS and unrelated
        markup before the HTML is sent to the AI extractor.

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
            if self._PRODUCT_PATH not in (url or ""):
                return soup
            if soup is None:
                return None

            compact = BeautifulSoup("<html><head></head><body></body></html>", "html.parser")
            keep_meta = {"og:title", "og:description", "og:url", "og:type", "og:image"}
            for meta in soup.find_all("meta"):
                key = meta.get("property") or meta.get("name")
                if key in keep_meta:
                    compact.head.append(meta)

            found = False
            for selector in ("#product_details", "#product_full_description", "#product_specifications"):
                for el in soup.select(selector):
                    compact.body.append(el)
                    found = True
            if not found:
                logger.warning(f"No Odoo product containers found for {url}")
                return soup
            logger.debug(f"Narrowed soup to Odoo product containers for {url}")
            return compact
        except Exception as e:
            logger.error(f"Error fetching page {url if 'url' in dir() else '?'}: {e}")
            return None

    # Sold-out detection: Odoo text detection on the oe_product_cart card.
    # Sold-out Odoo products carry a ribbon ("Sold out", "Out of stock",
    # "Temporarily out of stock") or an "Épuisé"/"Uitverkocht" badge inside the
    # product card. We check the specific card's text — never the whole page —
    # so embedded JSON blobs cannot false-positive.
    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from the Odoo category listing, filtering sold-out items.

        Args:
            store_url: URL of the coffee-beans category page

        Returns:
            List of in-stock product URLs
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        product_urls: list[str] = []
        seen: set[str] = set()

        for card in soup.select("article.oe_product_cart"):
            link = card.select_one(f'a[href*="{self._PRODUCT_PATH}"]')
            if not link:
                continue
            href = link.get("href")
            if not href or not isinstance(href, str):
                continue

            # Strip query string and fragment; resolve to absolute URL
            full_url = self.resolve_url(href.split("?")[0].split("#")[0])

            # Skip sold-out products before URL-pattern filtering
            card_text = card.get_text(" ", strip=True).lower()
            if any(
                marker in card_text
                for marker in (
                    "sold out",
                    "out of stock",
                    "temporarily out of stock",
                    "épuisé",
                    "epuise",
                    "uitverkocht",
                )
            ):
                logger.debug(f"Skipping sold-out product: {full_url}")
                continue

            # Drop brew-gear slugs (Fellow Atmos canisters) — sample packs are
            # kept and flagged as tasting kits downstream.
            slug = full_url.rstrip("/").rsplit("/", 1)[-1].lower()
            if any(excluded in slug for excluded in self._excluded_url_slugs):
                logger.debug(f"Excluding non-coffee product URL: {full_url}")
                continue

            # Apply standard coffee-product URL filtering
            if not self.is_coffee_product_url(full_url, required_path_patterns=[self._PRODUCT_PATH]):
                continue

            if full_url not in seen:
                seen.add(full_url)
                product_urls.append(full_url)

        logger.info(f"Found {len(product_urls)} in-stock product URLs from {store_url}")
        return product_urls

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Pin EUR as the store currency (default-currency-GBP fallback guard)."""
        bean.currency = "EUR"
        return bean
