"""Thankfully Coffee scraper implementation with AI extraction.

Thankfully Coffee (thankfullycoffee.com) is a Brooklyn, NY roaster specialising
in light and extra-light roast profiles sold in small 150g bags (plus 250g
espresso bags). The store is hosted on Shopify but has Shopify's JSON routes
disabled: ``/products.json``, ``/collections/*/products.json`` and
``/products/<handle>.json`` all return 404 (only ``?format=json`` responds,
with the regular HTML page). We therefore treat it like other JSON-less
storefronts (see routes.py / blue_hour.py):

- The curated coffee listing page (``/collections/coffee``) statically renders
  the whole bean catalogue as ``/products/<handle>`` links; the product
  sitemap (``/sitemap/products/1.xml``) is a known-good cross-check.
- Product pages are fully server-rendered with rich detail (varietal,
  region, altitude, harvest, process, sourcing story, tasting notes, and
  price with per-variant bag size / roast profile such as
  "150g - Standard Light" and "150g - Extra Light"), so plain HTTP fetches
  (no Playwright) are sufficient for AI extraction.
- Roast profiles are variants of the same product, not separate products, so
  no special product-level handling is needed.
"""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="thankfully-coffee",
    display_name="Thankfully",
    roaster_name="Thankfully",
    website="https://thankfullycoffee.com",
    description="Brooklyn, NY micro-roaster specialising in light and extra-light roasts "
    "of seasonal single origins, mostly sourced via Crop To Cup, sold in 150g bags",
    requires_api_key=True,
    currency="USD",
    country="United States",
    status="experimental",
)
class ThankfullyCoffeeScraper(BaseScraper):
    """Scraper for Thankfully Coffee (thankfullycoffee.com).

    Shopify-hosted but with JSON routes disabled, so the catalogue is
    enumerated from the rendered ``/collections/coffee`` page.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize the Thankfully Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Thankfully",
            base_url="https://thankfullycoffee.com",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        # Subscription products (the 2-Bag Subscription hides under the
        # generic handle `new-product`; the Roasters Choice plans use
        # `*-roasters-choice`).
        self.exclude_handles = {
            "new-product",
            "three-bags-per-month-roasters-choice",
            "5lb-bag-per-month-roasters-choice",
        }
        self.exclude_substrings = ("subscription", "roasters-choice")

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Return the curated coffee collection listing page."""
        return ["https://thankfullycoffee.com/collections/coffee"]

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract coffee product URLs from the rendered collection page.

        The listing page statically renders one ``/products/<handle>`` link per
        product, so a simple anchor scan recovers the full catalogue.
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        product_urls = []
        for anchor in soup.find_all("a", href=True):
            href = anchor["href"].split("?")[0].rstrip("/")
            if not href.startswith("/products/"):
                continue
            handle = href.split("/products/")[-1]
            if not handle or handle in self.exclude_handles:
                continue
            if any(sub in handle for sub in self.exclude_substrings):
                logger.debug(f"Skipping excluded product handle: {handle}")
                continue
            product_urls.append(f"{self.base_url}/products/{handle}")

        product_urls = list(dict.fromkeys(product_urls))
        logger.info(
            f"Found {len(product_urls)} coffee product URLs from {store_url} "
            f"(Shopify JSON routes are disabled on this store)"
        )
        return product_urls

    async def _scrape_new_products(
        self, product_urls: list[str], use_optimized_mode: bool = False
    ) -> list[CoffeeBean]:
        """Scrape new products using AI extraction from the static product pages."""
        if not product_urls:
            return []

        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=False,  # product pages are fully server-rendered
            use_optimized_mode=False,
        )

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Force USD — the store's JSON-LD reports USD for every offer."""
        bean.currency = "USD"
        return bean
