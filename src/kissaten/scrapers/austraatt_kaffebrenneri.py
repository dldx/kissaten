"""Austrått Kaffebrenneri scraper implementation with AI-powered extraction."""

import logging
import re

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="austraatt-kaffebrenneri",
    display_name="Austrått Kaffebrenneri",
    roaster_name="Austrått Kaffebrenneri",
    website="https://www.austraattkaffebrenneri.no",
    description="Norwegian specialty coffee roastery based in Voll, offering single-origin "
    "coffees and espresso blends.",
    requires_api_key=True,
    currency="NOK",
    country="Norway",
    status="available",
)
class AustraattKaffebrenneriScraper(BaseScraper):
    """Scraper for Austrått Kaffebrenneri with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Austrått Kaffebrenneri scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Austrått Kaffebrenneri",
            base_url="https://www.austraattkaffebrenneri.no",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        The old ``/categories/kaffe`` page was removed by the roaster and now
        returns a 404 ("Siden finnes ikke"). The shop moved to a Next.js
        storefront where ``/products`` lists every coffee in the catalogue.

        Returns:
            List of coffee store URLs.
        """
        return ["https://www.austraattkaffebrenneri.no/products"]

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page and return a reduced soup for AI extraction.

        For product pages, trim the soup down to the main product section
        (``main > section``) which contains the title, description, options
        and price - everything the AI extractor needs. Drops the rest of the
        page (header, footer, related products, reviews widgets, etc.) to
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

            if not isinstance(soup, (BeautifulSoup, Tag)) or "/products/" not in (url or ""):
                return soup

            section = soup.select_one("main > section")
            if not section:
                return soup

            trimmed = BeautifulSoup("", "lxml")
            trimmed.append(section)
            logger.debug(f"Trimmed product page to main section: {url}")
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
            translate_to_english=True,
        )

    def _get_excluded_url_patterns(self) -> list[str]:
        """Exclude non-bean products from the Austrått catalogue.

        Returns:
            List of URL patterns to exclude.
        """
        return super()._get_excluded_url_patterns() + [
            "espresso-og-baristamaskin",  # Espresso/barista coffee blend (not a single-origin bean)
            "abonnement",  # Subscription products
            "subscription",
            "brew-bag",
            "drip-bag",
            "capsule",
            "pod",
        ]

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Force currency to NOK regardless of AI detection."""
        bean.currency = "NOK"
        return super().postprocess_extracted_bean(bean)

    def _normalize_card_text(self, text: str) -> str:
        """Normalize card text to a slug-like form for exclusion matching.

        Norwegian/English product names on the storefront contain spaces and
        mixed casing (e.g. "Espresso og baristamaskin"). URL-pattern
        exclusions can't match them because many product URLs are UUID slugs
        (e.g. ``/products/404e7fb8-c9ea-4a65-a41f-20b68adbec72``). Normalizing
        card text (lowercase + runs of non-alphanumeric characters collapsed
        to single hyphens) lets the same exclusion patterns run against card
        text at the card level.

        Args:
            text: Raw card text

        Returns:
            Normalized, slug-like text
        """
        lowered = text.lower()
        return re.sub(r"[^a-z0-9æøå]+", "-", lowered).strip("-")

    def _get_card_title(self, card: Tag) -> str | None:
        """Extract the product title from a Next.js product card.

        The title lives in the ``alt`` attribute of the ``img`` tag inside the
        card's primary ``<a>`` link. Falling back to the link's own text keeps
        this working if the roaster renames/restructures the image markup.

        Args:
            card: The product card element

        Returns:
            Product title, or None if not found.
        """
        img = card.select_one('a[href*="/products/"] img[alt]')
        if isinstance(img, Tag):
            alt = img.get("alt")
            if isinstance(alt, str) and alt.strip():
                return alt.strip()
        link = card.select_one('a[href*="/products/"]')
        if isinstance(link, Tag):
            text = link.get_text(" ", strip=True)
            if text:
                return text
        return None

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from the /products listing page.

        Sold-out detection: text detection. Each Next.js product card says
        "På lager" (in stock) for available products and "Ikke på lager" /
        "Utsolgt" for sold-out ones. We skip cards that don't include the
        "På lager" marker before the standard coffee URL filter runs.

        Equipment exclusion: some products (e.g. the "Espresso og
        baristamaskin" machine bundle) use UUID slugs that URL-pattern
        exclusions can't match, so exclusions also run against normalized
        card text at the card level.

        Args:
            store_url: URL of the store page

        Returns:
            List of in-stock product URLs
        """
        soup = await self.fetch_page(store_url, use_playwright=False)
        if not soup:
            return []

        excluded_text_patterns = self._get_excluded_url_patterns()

        product_urls: list[str] = []
        seen: set[str] = set()
        for card in soup.select('div:has(> a[href*="/products/"])'):
            card_text = card.get_text(" ", strip=True)

            # Sold-out detection: text (Norwegian "På lager" = in stock).
            # In-stock cards never render a stock badge, but sold-out ones
            # explicitly show "Ikke på lager" / "Utsolgt", so skipping those
            # is equivalent to only returning in-stock products.
            if "Ikke på lager" in card_text or "Utsolgt" in card_text:
                logger.debug(f"Skipping sold-out product on {store_url}")
                continue

            # Equipment exclusion at card level (normalized title matching).
            # UUID product slugs mean URL-pattern exclusions can't match the
            # equipment bundle, so we match against the card title instead.
            title = self._get_card_title(card)
            if title is None:
                title = card_text
            normalized_text = self._normalize_card_text(title)
            if any(pattern in normalized_text for pattern in excluded_text_patterns):
                logger.debug(f"Skipping excluded (non-bean) product on {store_url}")
                continue

            link = card.select_one('a[href*="/products/"]')
            if not isinstance(link, Tag):
                continue
            href = link.get("href")
            if not href or not isinstance(href, str):
                continue

            full_url = self.resolve_url(href).split("?")[0]
            if self.is_coffee_product_url(full_url, required_path_patterns=["/products/"]):
                if full_url not in seen:
                    seen.add(full_url)
                    product_urls.append(full_url)

        logger.info(f"Found {len(product_urls)} in-stock product URLs from {store_url}")
        return product_urls
