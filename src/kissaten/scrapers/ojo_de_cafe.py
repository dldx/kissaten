"""Ojo de Café coffee roaster scraper implementation with AI-powered extraction."""

import logging
from urllib.parse import quote

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="ojo-de-cafe",
    display_name="Ojo de Café",
    roaster_name="Ojo de Café",
    website="https://www.ojodecafe.ch",
    description="Zurich-based specialty coffee roaster focusing on direct trade single-origin "
    "and espresso blends from Latin America.",
    requires_api_key=True,
    currency="CHF",
    country="Switzerland",
    status="available",
)
class OjoDeCafeScraper(BaseScraper):
    """Scraper for Ojo de Café (ojodecafe.ch) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Ojo de Café scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Ojo de Café",
            base_url="https://www.ojodecafe.ch",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List of coffee category URLs.
        """
        return ["https://www.ojodecafe.ch/shop?Kategorie=KAFFEE&CATEGORY=COFFEE&Category=COFFEE"]

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page and return a reduced soup for AI extraction.

        For product pages, trim the soup to the Wix ``[data-hook="product-page"]``
        wrapper which contains the image, title, description, price and
        options - everything the AI extractor needs. Drops the rest of the
        page (header, footer, related products, Wix runtime bundles) to
        reduce token count.

        Args:
            *args: Positional args forwarded to ``super().fetch_page``.
            **kwargs: Keyword args forwarded to ``super().fetch_page``.

        Returns:
            Reduced BeautifulSoup/Tag, or None if the fetch failed.
        """
        try:
            soup = await super().fetch_page(*args, **kwargs)
            url = kwargs.get("url")
            if not url and len(args) > 0:
                url = args[0]

            if not isinstance(soup, (BeautifulSoup, Tag)) or "/product-page/" not in (url or ""):
                return soup

            product_section = soup.select_one('[data-hook="product-page"]')
            if not product_section:
                return soup

            trimmed = BeautifulSoup("", "lxml")
            trimmed.append(product_section)
            logger.debug(f"Trimmed product page to [data-hook=product-page]: {url}")
            return trimmed
        except Exception as e:
            logger.error(f"Error fetching page {kwargs.get('url') or (args[0] if args else '?')}: {e}")
            return None

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
        """Force currency to CHF and drop beans with insufficient origin info.

        The AI extractor will happily return a bean with only the country set
        and every other origin field (region, farm, process, variety, altitude)
        blank. Those beans aren't useful for the search index, so we drop
        them here: the base class's own guard only requires *one* of
        country/process/variety to be present, which is too loose for this
        catalogue where every product page actually has full provenance.
        """
        bean.currency = "CHF"
        return super().postprocess_extracted_bean(bean)

    def _get_excluded_url_patterns(self) -> list[str]:
        """Exclude non-bean products (subscriptions, pads, gift cards, samplers).

        Returns:
            List of URL patterns to exclude.
        """
        return super()._get_excluded_url_patterns() + [
            "subscription",  # Subscription products
            "abonnement",
            "geschenkgutschein",  # Gift card (German)
            "gift-card",
            "giftcard",
            "gift",
            "probierset",  # Tasting/sampler set (German)
            "tasting-set",
            "taster-pack",
            "sample",
            "e-s-e-pads",  # E.S.E. coffee pads
            "ese-pads",
            "pads",
            "capsule",
            "pod",
        ]

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from the Kaffee category page.

        Sold-out detection: text detection. Wix renders a "Sold out" /
        "Ausverkauft" badge inside each product card; we skip any card
        that contains the sold-out text before the standard coffee URL
        filter runs.

        Args:
            store_url: URL of the store page

        Returns:
            List of in-stock product URLs
        """
        soup = await self.fetch_page(store_url, use_playwright=False)
        if not soup:
            return []

        product_urls: list[str] = []
        for card in soup.select('li[data-hook="product-list-grid-item"]'):
            card_text = card.get_text(" ", strip=True)
            # Sold-out detection: text (English "Sold out"/"Not available" or German "Ausverkauft")
            if "Sold out" in card_text or "Ausverkauft" in card_text or "Not available" in card_text:
                logger.debug(f"Skipping sold-out product on {store_url}")
                continue

            link = card.select_one('a[href*="/product-page/"]')
            if not isinstance(link, Tag):
                continue
            href = link.get("href")
            if not href or not isinstance(href, str):
                continue

            full_url = self.resolve_url(href).split("?")[0]
            # Wix serves slugs with literal non-ASCII characters ("mexico-cafeólogo-geisha"),
            # but Pydantic's HttpUrl serializes them percent-encoded. Normalize here so the
            # string-compare dedup against on-disk JSON files actually matches.
            full_url = quote(full_url, safe="/?:&=+#")
            if self.is_coffee_product_url(full_url, required_path_patterns=["/product-page/"]):
                product_urls.append(full_url)

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_urls: list[str] = []
        for url in product_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        logger.info(f"Found {len(unique_urls)} in-stock product URLs from {store_url}")
        return unique_urls
