"""Savage Roasters scraper implementation with AI-powered extraction (Shopify theme, HTML only)."""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="savage-roasters",
    display_name="Savage Roasters",
    roaster_name="Savage Roasters",
    website="https://www.savageroasters.coffee",
    description=(
        "Specialty coffee roaster based in Paris, France, selecting exceptional "
        "single-origin lots and roasting them in small batches."
    ),
    requires_api_key=True,
    currency="EUR",
    country="France",
    status="experimental",
)
class SavageRoastersScraper(BaseScraper):
    """Scraper for Savage Roasters (savageroasters.coffee).

    The storefront runs the Shopify Dawn theme but disables the ``products.json``
    endpoint (404), so discovery uses the server-rendered ``/collections/all``
    listing HTML and the Dawn ``?filter.v.availability=1`` in-stock filter
    instead of the Shopify JSON API. The site is French-language.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Savage Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Savage Roasters",
            base_url="https://www.savageroasters.coffee",
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
        """Get store URLs to scrape.

        Dawn supports the ``?filter.v.availability=1`` in-stock query param
        (sold-out checklist step 1), so only in-stock products are listed.

        Returns:
            List containing the all-products collection URL with the availability filter.
        """
        return ["https://www.savageroasters.coffee/collections/all?filter.v.availability=1"]

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
            translate_to_english=True,  # French site — translate to English
        )

    # Sold-out detection: URL filter param is the primary mechanism
    # (?filter.v.availability=1, applied in get_store_urls). As a fallback the
    # Dawn product-card text is also checked for the French/English sold-out
    # markers ("Épuisé", "Rupture de stock", "Sold out") on the specific
    # .card-wrapper product card — never on the whole page, so embedded JSON
    # blobs cannot false-positive.
    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from the Dawn collection listing, filtering sold-out items.

        Args:
            store_url: URL of the collection listing page

        Returns:
            List of in-stock product URLs
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        product_urls: list[str] = []
        seen: set[str] = set()

        cards = soup.select(".card-wrapper.product-card-wrapper")
        if not cards:
            # Fallback: raw product anchors (e.g. if the theme markup changes)
            cards = [
                a.parent.parent if a.parent and a.parent.parent else a for a in soup.select('a[href*="/products/"]')
            ]

        for card in cards:
            link = card.select_one('a[href*="/products/"]')
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
                marker in card_text for marker in ("épuisé", "epuise", "rupture de stock", "sold out", "out of stock")
            ):
                logger.debug(f"Skipping sold-out product: {full_url}")
                continue

            # Apply standard coffee-product URL filtering (uses /products/ path pattern)
            if not self.is_coffee_product_url(full_url, required_path_patterns=["/products/"]):
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
