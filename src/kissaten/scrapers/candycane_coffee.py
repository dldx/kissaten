"""Candycane Coffee scraper implementation with AI-powered extraction.

Platform: bespoke Laravel + Livewire + Tailwind storefront (Czech-language, founded in
Prague). The coffee category ``/kategorie/kava`` renders product cards as
``a[data-context="product_card"]`` anchors pointing at ``/produkty/<slug>``
(both desktop and mobile variants, hence duplicate anchors to de-duplicate).
Model scraper used: ``koppi.py`` (minimal static-HTML + AI extraction).

Note: the Fermentation Project roster lists this roaster under Poland/PLN, but the
storefront is unambiguously Czech — ``lang="cs"``, prices in ``Kč`` with a
``"currency":"CZK"`` JSON blob, and the roastery is described as founded in Prague — so
the verified country/currency are Czechia/CZK.
"""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="candycane-coffee",
    display_name="Candycane Coffee",
    roaster_name="Candycane Coffee",
    website="https://www.candycane.coffee",
    description=(
        "Czech specialty coffee roastery founded in Prague in 2017, roasting "
        "single-origin filter and espresso coffees and chocolate-covered beans."
    ),
    requires_api_key=True,
    currency="CZK",
    country="Czechia",
    status="experimental",
)
class CandycaneCoffeeScraper(BaseScraper):
    """Scraper for Candycane Coffee (candycane.coffee) with AI extraction."""

    #: Coffee category listing.
    STORE_URL = "https://www.candycane.coffee/kategorie/kava"

    def __init__(self, api_key: str | None = None):
        """Initialize Candycane Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Candycane Coffee",
            base_url="https://www.candycane.coffee",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get the coffee category URL."""
        return [self.STORE_URL]

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract in-stock coffee product URLs from the Livewire category page.

        # Sold-out detection: card-level text detection on each
        # ``a[data-context="product_card"]`` card. Shopify-style sold-out badges are
        # not used here; the WooCommerce/Livewire "Do košíku" (add to cart) button is
        # replaced by a "Vyprodáno" label when sold out. The check runs on the card
        # text only and before ``is_coffee_product_url`` filtering.
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        product_urls: list[str] = []
        for card in soup.select('a[data-context="product_card"]'):
            href = card.get("href")
            if not href or not isinstance(href, str):
                continue

            card_text = " ".join(card.get_text(" ", strip=True).split()).lower()
            if "vyprod" in card_text or "sold out" in card_text or "není skladem" in card_text:
                logger.debug(f"Skipping sold-out product card: {href}")
                continue

            full_url = self.resolve_url(href.split("?")[0].split("#")[0])
            if not self.is_coffee_product_url(full_url, required_path_patterns=["/produkty/"]):
                continue
            product_urls.append(full_url)

        # The grid renders each product twice (desktop + mobile), so de-duplicate.
        product_urls = list(dict.fromkeys(product_urls))

        # Exclude non-coffee products: chocolate-covered beans, cascara tea, coffee
        # capsules, office subscriptions, courses, equipment, merchandise and vouchers.
        excluded = [
            "home-office",
            "kancl",
            "cascara",
            "cokolad",
            "kapsle",
            "kurzy",
            "workshopy",
            "prislusenstvi",
            "mlynky",
            "filtry",
            "merch",
            "darkova",
            "darkovy",
            "poukaz",
        ]
        coffee_urls = [url for url in product_urls if not any(ex in url.lower() for ex in excluded)]

        logger.info(f"Found {len(coffee_urls)} coffee product URLs out of {len(product_urls)} total from {store_url}")
        return coffee_urls

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction (Czech → English)."""
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

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Pin CZK — the registry default-currency lookup falls back to GBP for hyphenated names."""
        bean.currency = "CZK"
        return bean
