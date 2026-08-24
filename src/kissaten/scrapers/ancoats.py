"""Ancoats Coffee Co. scraper implementation with AI extraction (WooCommerce).

Ancoats Coffee Co. (www.ancoats-coffee.co.uk) is a WordPress + WooCommerce +
Divi storefront. The verified live domain is the hyphenated
``www.ancoats-coffee.co.uk`` (the checklist plain ``ancoatscoffee.co.uk`` is
dead). The WooCommerce Store API (``/wp-json/wc/store/v1/products``) returns
429, so discovery and extraction run off server-rendered HTML.

The category pages under ``/products/coffee/`` list product cards linking to
``/store/<category>/<subcategory>/<slug>/?select=1``. We strip the ``?select=1``
query and resolve to the canonical product page, which the Divi theme renders
as a single ``div.product`` container carrying price, description, and the
bean fact table (Producer / Cup Profile / Country / Preparation / Terroir /
Genetics / Altitude / Cup Score).

Subscriptions (``/store/subscriptions/``, ``/store/1kgsubs/``) are a genuine
service and are excluded; tasting-kit/sampler products are NOT excluded (the
base ``_apply_product_flags`` flags any kit it finds for admin review).
"""

import logging

from bs4 import BeautifulSoup

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="ancoats",
    display_name="Ancoats Coffee Co.",
    roaster_name="Ancoats Coffee Co.",
    website="https://www.ancoats-coffee.co.uk",
    description=(
        "Independent specialty coffee roaster based in Ancoats, Manchester, "
        "sourcing single-origin coffees with transparency (WooCommerce)."
    ),
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class AncoatsScraper(BaseScraper):
    """Scraper for Ancoats Coffee Co. (ancoats-coffee.co.uk) with AI extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize The Ancoats scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Ancoats Coffee Co.",
            base_url="https://www.ancoats-coffee.co.uk",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get the coffee category listing URLs (server-rendered WooCommerce)."""
        return [
            "https://www.ancoats-coffee.co.uk/products/coffee/",
            "https://www.ancoats-coffee.co.uk/products/coffee/single-origin/",
        ]

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction."""

        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=False,
            use_optimized_mode=False,
        )

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Pin GBP as the store currency (final guard)."""
        bean.currency = "GBP"
        return bean

    async def fetch_page(self, *args, **kwargs):
        """Narrow product pages to the Divi product-detail container.

        Ancoats renders each product inside a single ``div.product`` section
        (price, description, cup fact table, add-to-basket). We send only that
        to the AI to keep token usage down; listing/category pages are left
        intact so card extraction still works.
        """
        soup = await super().fetch_page(*args, **kwargs)
        url = kwargs.get("url") or (args[0] if args else "")
        if not soup or "/store/" not in url:
            return soup

        product_container = soup.select_one("div.product")
        if product_container is None:
            return soup
        logger.debug(f"Pruned product page to div.product for {url}")
        wrapper = BeautifulSoup("<html><head></head><body></body></html>", "html.parser")
        wrapper.body.append(product_container)
        return wrapper

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from the WooCommerce category page.

        # Sold-out detection: card-level text check on each ``li.product``
        # WooCommerce card. Sold-out items carry "Out of stock" / "Sold out"
        # text on the card (never a whole-page search).
        """
        soup = await self.fetch_page(store_url, use_playwright=False)
        if not soup:
            return []

        all_product_urls = []
        # WooCommerce/Divi renders product cards as ``li.product`` with a
        # ``woocommerce-loop-product__title`` and a link to /store/.../
        for card in soup.select("li.product"):
            card_text = " ".join(card.get_text(" ", strip=True).split()).lower()
            if "out of stock" in card_text or "sold out" in card_text:
                continue
            for a in card.find_all("a", href=True):
                href = a["href"]
                if "/store/" not in href:
                    continue
                # Etsy-style ?select=1 query is added by Divi's card overrides;
                # canonical product pages drop it.
                canonical_url = self.resolve_url(href.split("?")[0])
                all_product_urls.append(canonical_url)

        # Filter: genuine services (subscriptions) only. No tasting-kit tokens.
        coffee_urls = []
        for url in all_product_urls:
            if not self.is_coffee_product_url(url, required_path_patterns=["/store/"]):
                continue
            if any(tok in url.lower() for tok in ["subscription", "subscriptions", "1kgsubs"]):
                continue
            coffee_urls.append(url)

        coffee_urls = list(dict.fromkeys(coffee_urls))
        logger.info(f"Found {len(coffee_urls)} available product URLs from {store_url}")
        return coffee_urls
