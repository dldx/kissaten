"""The Roasting Project scraper implementation with AI-powered extraction.

The Roasting Project is a Fife (Kirkcaldy, 5 Oswald Road KY1 3JE) roastery
selling on a WordPress + WooCommerce storefront at www.theroastingproject.co.uk
(the non-www host 301-redirects to www). The catalogue is a small set of
whole-bean coffees (blends + single-origins) on /buy-coffee/, plus a large
"kit" category of grinders / drippers / moka pots / cups and a couple of
coffee-subscription options.

Discovery uses the public unauthenticated WooCommerce Store API (product
listing + prices/variants + per-product categories), filtering to the
``coffee`` category and dropping subscription plans. Per-product bean fields
(origin, process, tasting notes, weight, etc.) come from AI extraction of each
product's JSON-LD-annotated HTML page — mirroring the the_lost_barn /
santu_coffee pattern.
"""

import json
import logging
import re

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)

# Public WooCommerce Store API endpoint for product discovery. Returns the full
# current catalogue (whole-bean coffees, subscription options, and kit/equipment)
# with prices, variants, categories and canonical permalinks, which we filter
# down to whole-bean coffee below.
STORE_API_URL = "https://www.theroastingproject.co.uk/wp-json/wc/store/v1/products?per_page=100"

# Product category that marks a product as whole-bean coffee. Equipment/merch
# lives in the "kit" category and subscriptions in "subscriptions"; neither is
# coffee. Samplers/tasting kits are intentionally NOT excluded here (there are
# none in the current catalogue) so they land in the admin review queue rather
# than being silently dropped.
COFFEE_CATEGORY = "coffee"

# Recurring-delivery subscription plans (e.g. "Buy for 3/6/12 Months",
# "Rolling Subscription") are excluded. The whole-bean names never contain these.
SUBSCRIPTION_NAME_RE = re.compile(r"\b(?:subscription|buy for|months)\b", re.IGNORECASE)


@register_scraper(
    name="the-roasting-project",
    display_name="The Roasting Project",
    roaster_name="The Roasting Project",
    website="https://www.theroastingproject.co.uk",
    description="Fife (Kirkcaldy) roastery offering small-batch whole-bean blends and "
    "single-origin coffees alongside brewing equipment and subscription plans "
    "(WooCommerce storefront).",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class TheRoastingProjectScraper(BaseScraper):
    """Scraper for The Roasting Project (theroastingproject.co.uk) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize The Roasting Project scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="The Roasting Project",
            base_url="https://www.theroastingproject.co.uk",
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

        Returns the public WooCommerce Store API endpoint. The API is the
        authoritative, current in-stock catalogue and exposes the product
        permalinks (canonical ``/product/<slug>/`` URLs) used for extraction.

        Returns:
            List containing the WooCommerce Store API URL.
        """
        return [STORE_API_URL]

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from the WooCommerce Store API.

        # Sold-out detection: API ``is_in_stock`` flag
        The Store API exposes an ``is_in_stock`` boolean per product, so no
        HTML class/text scanning is needed. We filter to products in the
        ``coffee`` category and drop subscription plans before running
        ``is_coffee_product_url`` so excluded non-coffee products (kit/equipment,
        subscriptions) can never leak past the stock check. Sampler/tasting-kit
        products are deliberately not excluded.

        Args:
            store_url: URL of the WooCommerce Store API endpoint.

        Returns:
            List of whole-bean product URLs found via the API.
        """
        product_urls: list[str] = []

        response = await self.client.get(store_url)
        response.raise_for_status()
        try:
            products = json.loads(response.text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Store API JSON from {store_url}: {e}")
            self._failed_listing_urls.append(store_url)
            return product_urls

        if not isinstance(products, list):
            logger.error(f"Unexpected Store API payload (expected a list) from {store_url}")
            self._failed_listing_urls.append(store_url)
            return product_urls

        for product in products:
            # Sold-out products are not in the current catalogue.
            if product.get("is_in_stock") is False:
                logger.debug(f"Skipping sold-out product: {product.get('name')}")
                continue

            name = product.get("name") or ""
            product_type = (product.get("type") or "").lower()
            categories = {cat.get("slug", "") for cat in (product.get("categories") or [])}

            # Keep only whole-bean coffee. The "kit" category (equipment/merch)
            # and "subscriptions" category are dropped. Samplers are not excluded.
            if COFFEE_CATEGORY not in categories:
                logger.debug(f"Skipping non-coffee product: {name}")
                continue

            # Drop recurring-delivery subscription plans (incl. variable-subscription).
            if (
                "subscription" in product_type
                or "subscriptions" in categories
                or SUBSCRIPTION_NAME_RE.search(name)
            ):
                logger.debug(f"Skipping subscription product: {name}")
                continue

            href = product.get("permalink")
            if not isinstance(href, str) or not href:
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

        logger.info(f"Found {len(unique_urls)} product URLs from Store API (whole-bean, in-stock)")
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
