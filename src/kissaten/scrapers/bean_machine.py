"""Bean Machine scraper implementation with AI-powered extraction.

Platform: WordPress + WooCommerce with JetEngine product grids (Danish storefront).
The "Kaffe" category is served through the JetEngine filter query
``/shop/?jsf=jet-woo-products-grid&tax=product_cat:17`` and renders
``div.jet-woo-products__item`` cards linking to ``/shop/nyristet-kaffe/<slug>/``.
Model scraper used: ``koppi.py`` (minimal static-HTML + AI extraction).
"""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="bean-machine",
    display_name="Bean Machine",
    roaster_name="Bean Machine",
    website="https://www.beanmachine.dk",
    description=(
        "Danish specialty coffee roaster and coffee bar in Copenhagen selling "
        "freshly roasted single origins, blends and The Fermentation Project tasting kit."
    ),
    requires_api_key=True,
    currency="DKK",
    country="Denmark",
    status="experimental",
)
class BeanMachineScraper(BaseScraper):
    """Scraper for Bean Machine (beanmachine.dk) with AI extraction."""

    #: JetEngine-filtered WooCommerce "Kaffe" category (product_cat:17).
    STORE_URL = "https://www.beanmachine.dk/shop/?jsf=jet-woo-products-grid&tax=product_cat:17"

    def __init__(self, api_key: str | None = None):
        """Initialize Bean Machine scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Bean Machine",
            base_url="https://www.beanmachine.dk",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get the freshly-roasted coffee (Kaffe) category URL."""
        return [self.STORE_URL]

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract in-stock coffee product URLs from the JetEngine product grid.

        # Sold-out detection: WooCommerce class detection on the JetEngine card
        # (``outofstock`` class) plus Danish text fallback ("udsolgt", "ikke på lager").
        Applied before ``is_coffee_product_url`` filtering.
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        product_urls: list[str] = []
        cards = soup.select("div.jet-woo-products__item") or soup.select("li.product")
        for card in cards:
            link = card.select_one('a[href*="/shop/nyristet-kaffe/"]')
            if not link or not isinstance(link.get("href"), str):
                continue

            card_classes = " ".join(card.get("class") or []).lower()
            card_text = " ".join(card.get_text(" ", strip=True).split()).lower()
            if (
                "outofstock" in card_classes
                or "sold-out" in card_classes
                or "udsolgt" in card_text
                or "ikke på lager" in card_text
            ):
                logger.debug(f"Skipping sold-out product card: {link['href']}")
                continue

            full_url = self.resolve_url(link["href"].split("?")[0].split("#")[0])
            if not self.is_coffee_product_url(full_url, required_path_patterns=["/shop/nyristet-kaffe/"]):
                continue
            product_urls.append(full_url)

        product_urls = list(dict.fromkeys(product_urls))

        # Exclude equipment, subscriptions and courses (keep the tasting kit).
        excluded = [
            "udstyr",
            "abonnement",
            "kaffeabonnement",
            "kursus",
            "kurser",
            "gavekort",
            "maskine",
            "tilbehør",
        ]
        coffee_urls = [url for url in product_urls if not any(ex in url.lower() for ex in excluded)]

        logger.info(f"Found {len(coffee_urls)} coffee product URLs out of {len(product_urls)} total from {store_url}")
        return coffee_urls

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction (Danish → English)."""
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
        """Pin DKK — the registry default-currency lookup falls back to GBP for hyphenated names."""
        bean.currency = "DKK"
        return bean
