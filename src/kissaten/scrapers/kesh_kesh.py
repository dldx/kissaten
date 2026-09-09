"""Kesh Kesh Coffee Roastery scraper implementation with AI-powered extraction (WooCommerce).

Note on identity: the roaster the brand story traces back to is Kesh Kesh Coffee
Roasters of Nairobi, Kenya (Timau Plaza, Kilimani), but the Nairobi business has
no online bean shop. This scraper targets the brand's WooCommerce store in
Calgary, Alberta, Canada (keshkeshroastery.com), which ships across Canada and
prices in CAD. See openwiki/roasters/kesh_kesh.md for the full verification.
"""

import logging

from bs4 import BeautifulSoup

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="kesh-kesh",
    display_name="Kesh Kesh Coffee Roastery",
    roaster_name="Kesh Kesh Coffee Roastery",
    website="https://keshkeshroastery.com",
    description="Calgary-based specialty coffee roastery rooted in the Eritrean coffee ceremony, "
    "sourcing East African Arabica and shipping freshly roasted coffee across Canada",
    requires_api_key=True,
    currency="CAD",
    country="Canada",
    status="available",
)
class KeshKeshScraper(BaseScraper):
    """Scraper for Kesh Kesh Coffee Roastery (keshkeshroastery.com, WooCommerce).

    The catalogue is tiny (two variable roast products: Jebena Medium Roast and
    Fernelo Dark Roast, each offered in multiple weights and with Origin as a
    per-order variant choice: Kenya/Ethiopia/Uganda/Rwanda/Costa Rica). Product
    pages are fully server-rendered, so no Playwright is needed. Because the
    origin is a customer-selected variant rather than a fixed bean attribute,
    extracted beans may legitimately have no single origin.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Kesh Kesh Coffee Roastery scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Kesh Kesh Coffee Roastery",
            base_url="https://keshkeshroastery.com",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the WooCommerce shop URL
        """
        return ["https://keshkeshroastery.com/shop/"]

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
            use_playwright=False,  # Product pages are fully server-rendered
            use_optimized_mode=False,
            translate_to_english=False,
        )

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from the WooCommerce shop page.

        Returns:
            List of product URLs
        """
        soup = await self.fetch_page(store_url, use_playwright=False)
        if not soup:
            return []

        # Sold-out detection: WooCommerce stamps each product card (li.product)
        # with `instock` or `outofstock`; skip cards marked out of stock before
        # any coffee filtering.
        all_product_urls = []
        for link in soup.select("li.product a.woocommerce-LoopProduct-link"):
            card = link.find_parent("li", class_="product")
            if card and "outofstock" in (card.get("class") or []):
                logger.debug(f"Skipping out-of-stock product card: {link.get('href')}")
                continue
            href = link.get("href")
            if href and isinstance(href, str):
                all_product_urls.append(self.resolve_url(href))

        # Product URLs are root-level slugs (e.g. /jebena-medium-roast/) with no
        # /product/ segment, so pass a base-domain pattern that lets
        # is_coffee_product_url apply its standard exclusion lists.
        filtered_urls = []
        for url in self.deduplicate_urls(all_product_urls):
            if self.is_coffee_product_url(url, required_path_patterns=["keshkeshroastery.com/"]):
                filtered_urls.append(url)

        logger.info(f"Found {len(filtered_urls)} available product URLs from {store_url}")
        return filtered_urls

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | None:
        """Narrow product detail pages to the product container to save tokens.

        Kesh Kesh product pages are Elementor-built (~270 KB) with a large
        header/footer; the product content (summary, description tab,
        additional-information tab, meta) lives inside ``div#primary``.
        Listing pages are left untouched.

        Returns:
            Narrowed (or original) BeautifulSoup object
        """
        soup = await super().fetch_page(*args, **kwargs)
        if not soup:
            return soup

        container = soup.select("div#primary")
        if len(container) == 1:
            # Drop the "Related products" carousel — pure noise for extraction.
            for related in soup.select("section.related.products"):
                related.decompose()
            return container[0]
        return soup

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Pin the currency to CAD as a final guard.

        The store prices in CAD (confirmed via the WooCommerce Store API);
        never let AI-extracted or default currencies leak through.

        Returns:
            Postprocessed CoffeeBean object
        """
        bean.currency = "CAD"
        return bean
