"""Winchester Coffee Roasters scraper implementation with AI-powered extraction.

Winchester Coffee Roasters is a Hampshire (Sun Valley Business Park, Winnall,
Winchester) roaster selling on a WordPress + WooCommerce storefront at
winchestercoffeeroasters.co.uk. The live catalogue is a small set of whole-bean
coffees (blends + single-origins) shown on /shop/ (roughly 17 products).

Discovery: the public WooCommerce REST/Store API is blocked (``/wp-json/`` and
``/wp-json/wc/store/v1/products`` both return HTTP 401 "Only authenticated
users can access the REST API"), so this scraper falls back to HTML enumeration
of the server-rendered /shop/ listing page. Per-product bean fields (origin,
process, tasting notes, weight, etc.) come from AI extraction of each product's
JSON-LD-annotated HTML page — mirroring the the_lost_barn / the_roasting_project
pattern.
"""

import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)

# Server-rendered WooCommerce shop listing. This is the authoritative, current
# in-stock catalogue of whole-bean coffees (single-origins + blends).
SHOP_URL = "https://winchestercoffeeroasters.co.uk/shop/"

# Product category CSS classes that mark a card as whole-bean coffee. Equipment
# and machines live under separate "machines-equipment" / "equipment" /
# "barista-shop" categories. Samplers/tasting kits (none in the current
# catalogue) are intentionally not excluded so they land in the admin review
# queue rather than being silently dropped.
COFFEE_CATEGORY_CLASSES = ("product_cat-shop-online", "product_cat-single-origin", "product_cat-blends")
EQUIPMENT_CATEGORY_CLASSES = (
    "product_cat-machines-equipment",
    "product_cat-equipment",
    "product_cat-equipment-old",
    "product_cat-barista-shop",
    "product_cat-by-manufacturer",
)


@register_scraper(
    name="winchester",
    display_name="Winchester Coffee Roasters",
    roaster_name="Winchester Coffee Roasters",
    website="https://winchestercoffeeroasters.co.uk",
    description="Winchester (Sun Valley Business Park, Winnall) roaster offering "
    "small-batch whole-bean blends and single-origin coffees plus a range of "
    "brewing equipment and machines (WooCommerce storefront).",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class WinchesterCoffeeRoastersScraper(BaseScraper):
    """Scraper for Winchester Coffee Roasters (winchestercoffeeroasters.co.uk) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Winchester Coffee Roasters scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Winchester Coffee Roasters",
            base_url="https://winchestercoffeeroasters.co.uk",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=60.0,
        )

        # Store is UK/GBP native. Pin the currency defensively so the AI
        # extractor never sees a wrong geo-detected currency.
        self.store_currency = "GBP"
        self._currency_detected = True

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns the server-rendered /shop/ listing. The public WooCommerce
        REST/Store API is 401-blocked, so the shop page is the authoritative
        current catalogue and exposes the canonical ``/product/<slug>/`` URLs
        used for extraction.

        Returns:
            List containing the /shop/ listing URL.
        """
        return [SHOP_URL]

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from the /shop/ listing HTML.

        # Sold-out detection: WooCommerce ``li.product`` ``outofstock`` class
        Each product card is a ``<li class="product ... instock|outofstock ...">``.
        We skip cards whose ``li`` carries the ``outofstock`` class (or whose card
        text mentions "Out of stock"/"Sold out") before extracting the product
        permalink, and we drop non-coffee cards (equipment/machines categories)
        before running ``is_coffee_product_url`` so excluded products can never
        leak past the stock check. Sampler/tasting-kit products are not excluded.

        Args:
            store_url: URL of the /shop/ listing page.

        Returns:
            List of whole-bean product URLs found on the listing page.
        """
        product_urls: list[str] = []

        soup = await self.fetch_page(store_url, use_playwright=False)
        if not soup:
            self._failed_listing_urls.append(store_url)
            return product_urls

        for card in soup.select("li.product"):
            # Sold-out detection: the WooCommerce <li> carries an outofstock class.
            card_classes = set(card.get("class") or [])
            if "outofstock" in card_classes:
                logger.debug("Skipping sold-out product card on %s", store_url)
                continue

            # Belt-and-braces text fallback (WooCommerce sometimes only marks
            # stock on the detail page). Scope to the card only — never a whole
            # page text search, which false-positives on embedded JSON/CSS.
            card_text = card.get_text(" ", strip=True)
            if "out of stock" in card_text.lower() or "sold out" in card_text.lower():
                logger.debug("Skipping sold-out product card (text) on %s", store_url)
                continue

            # Keep whole-bean coffee; drop equipment/machines categories.
            if not any(c in card_classes for c in COFFEE_CATEGORY_CLASSES):
                logger.debug("Skipping non-coffee product card on %s", store_url)
                continue
            if any(c in card_classes for c in EQUIPMENT_CATEGORY_CLASSES):
                logger.debug("Skipping equipment/machine product card on %s", store_url)
                continue

            link = card.select_one("a.woocommerce-loop-product__link")
            if link is None:
                link = card.select_one("a.woocommerce-LoopProduct-link")
            if link is None:
                continue

            href = link.get("href")
            if not href or not isinstance(href, str):
                continue

            full_url = self.resolve_url(href)
            # Strip query string before checking/adding to database.
            if "?" in full_url:
                full_url = full_url.split("?")[0]

            if self.is_coffee_product_url(full_url, required_path_patterns=["/product/"]):
                product_urls.append(full_url)

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_urls: list[str] = []
        for url in product_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        logger.info(f"Found {len(unique_urls)} product URLs from {store_url} (whole-bean, in-stock)")
        return unique_urls

    async def _scrape_new_products(self, product_urls: list[str], use_optimized_mode: bool = False) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction.

        Args:
            product_urls: List of new product URLs to extract.
            use_optimized_mode: Whether to use optimized (screenshot) mode.

        Returns:
            List of newly scraped CoffeeBean objects.
        """
        if not product_urls:
            return []

        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=False,  # WooCommerce product pages are server-rendered
            use_optimized_mode=use_optimized_mode,
        )

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Force GBP currency and clean query strings from the URL."""
        bean.currency = "GBP"
        if bean.url and "?" in str(bean.url):
            # Clean URL to match database schema conventions without query parameters
            from urllib.parse import unquote, urlsplit, urlunsplit

            decoded = unquote(str(bean.url))
            parts = urlsplit(decoded)
            bean.url = urlunsplit(parts._replace(query=""))

        return super().postprocess_extracted_bean(bean)
