"""San Agustín Tostadores De Café scraper implementation with AI-powered extraction.

Platform: WordPress + WooCommerce (Spanish-language storefront). Product cards are
server-rendered ``li.product`` elements with ``a.woocommerce-LoopProduct-link`` links
using the ``/producto/<slug>/`` permalink pattern and per-card ``outofstock`` classes.
Model scraper used: ``koppi.py`` (minimal static-HTML + AI extraction).
"""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="san-agustin",
    display_name="San Augustín Tostadores De Café",
    roaster_name="San Augustín Tostadores De Café",
    website="https://sanagustin.com",
    description=(
        "Spanish specialty coffee roaster (San Agustín) selling single-origin "
        "microlots, blends and decaf, including The Fermentation Project by James Hoffmann."
    ),
    requires_api_key=True,
    currency="EUR",
    country="Spain",
    status="experimental",
)
class SanAgustinScraper(BaseScraper):
    """Scraper for San Agustín Tostadores De Café (sanagustin.com) with AI extraction."""

    #: Coffee category archive — the only category that holds roasted coffee.
    STORE_URL = "https://www.sanagustin.com/categoria-producto/el-mejor-cafe-del-mundo/"

    def __init__(self, api_key: str | None = None):
        """Initialize San Agustín scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="San Augustín Tostadores De Café",
            base_url="https://www.sanagustin.com",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get the freshly-roasted coffee category URL."""
        return [self.STORE_URL]

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract in-stock coffee product URLs from the WooCommerce category page.

        # Sold-out detection: WooCommerce class detection on the ``li.product`` card
        # (``outofstock`` class) plus Spanish text fallback ("agotado"). Applied before
        # ``is_coffee_product_url`` so excluded products cannot leak past the stock check.
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        product_urls: list[str] = []
        for card in soup.select("li.product"):
            link = card.select_one('a.woocommerce-LoopProduct-link[href*="/producto/"]') or card.select_one(
                'a[href*="/producto/"]'
            )
            if not link or not isinstance(link.get("href"), str):
                continue

            card_classes = " ".join(card.get("class") or []).lower()
            card_text = " ".join(card.get_text(" ", strip=True).split()).lower()
            if "outofstock" in card_classes or "sold-out" in card_classes or "agotado" in card_text:
                logger.debug(f"Skipping sold-out product card: {link['href']}")
                continue

            full_url = self.resolve_url(link["href"].split("?")[0].split("#")[0])
            if not self.is_coffee_product_url(full_url, required_path_patterns=["/producto/"]):
                continue
            product_urls.append(full_url)

        product_urls = list(dict.fromkeys(product_urls))

        # Exclude genuine equipment/merch/services (Spanish slugs), but keep the
        # Fermentation Project tasting kit (handled by tasting-kit flagging downstream).
        excluded = [
            "herramientas",
            "cafeteras",
            "molinos",
            "marzocco",
            "mahlkonig",
            "dulces",
            "suscripcion",
            "suscripción",
            "abono",
            "curso",
            "formacion",
            "formación",
            "profesional",
            "gift",
            "tarjeta",
            "regalo",
        ]
        coffee_urls = [url for url in product_urls if not any(ex in url.lower() for ex in excluded)]

        logger.info(f"Found {len(coffee_urls)} coffee product URLs out of {len(product_urls)} total from {store_url}")
        return coffee_urls

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction (Spanish → English)."""
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
        """Pin EUR — the registry default-currency lookup falls back to GBP for hyphenated names."""
        bean.currency = "EUR"
        return bean
