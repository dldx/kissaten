"""Neighbourhood Coffee scraper implementation with AI-powered extraction.

Neighbourhood Coffee is a Liverpool (Unit 22, The Sandon Estate, L5 9YN)
roastery selling on a WordPress + WooCommerce storefront at
www.neighbourhoodcoffee.co.uk. The catalogue is a set of whole-bean coffees
(blends + single-origins grouped by growing region) on /product-category/coffee/,
plus a large "coffee equipment" catalogue (Sage/Hario/Fellow/AeroPress/Chemex),
a "gifting" range (t-shirts, candles, gift vouchers, mugs), and a handful of
coffee-subscription plans.

Discovery uses the public unauthenticated WooCommerce Store API (product
listing + prices/variants + per-product categories), filtering to the
whole-bean origin/type coffee categories and dropping equipment,
subscriptions, and gifts. Per-product bean fields (origin, process, tasting
notes, weight, etc.) come from AI extraction of each product's HTML page,
mirroring the the_roasting_project / the_lost_barn pattern.
"""

import json
import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)

# Public WooCommerce Store API endpoint for product discovery. Returns the full
# current catalogue (whole-bean coffees, equipment, gifts, subscriptions) with
# prices, variants, categories and canonical permalinks, which we filter down
# to whole-bean coffee below.
STORE_API_URL = "https://www.neighbourhoodcoffee.co.uk/wp-json/wc/store/v1/products?per_page=100"

# Neighbourhood has no flat "coffee" category; whole-bean coffees live in
# origin/type subcategories (by growing region or blend type). Products in
# these categories are whole-bean coffee. Everything else — equipment
# ("coffee-equipment", "hario", "fellow-coffee-equipment", "sage-*", etc.),
# subscriptions ("coffee-subscriptions") and gift items ("gifting",
# "christmas") — is not coffee and is dropped. Curated sampler/tasting
# collections ("collections-coffee") are intentionally kept so they land in
# the admin review queue rather than being silently excluded.
COFFEE_CATEGORIES = {
    "africa-coffee",
    "south-america-coffee",
    "central-america-coffee",
    "blends-coffee",
    "decaf-coffee",
    "india-coffee",
    "collections-coffee",
}

# Recurring-delivery subscription plans (e.g. "Espresso Lovers Coffee
# Subscription") are excluded. Whole-bean names never contain these tokens.
SUBSCRIPTION_TOKENS = ("subscription", "variable-subscription")


@register_scraper(
    name="neighbourhood",
    display_name="Neighbourhood Coffee",
    roaster_name="Neighbourhood Coffee",
    website="https://www.neighbourhoodcoffee.co.uk",
    description="Liverpool (The Sandon Estates, L5 9YN) roastery offering whole-bean blends "
    "and single-origin coffees alongside brewing equipment, subscriptions and "
    "gifts (WooCommerce storefront).",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class NeighbourhoodScraper(BaseScraper):
    """Scraper for Neighbourhood Coffee (neighbourhoodcoffee.co.uk) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Neighbourhood Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Neighbourhood Coffee",
            base_url="https://www.neighbourhoodcoffee.co.uk",
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
        whole-bean coffee origin/type categories and drop subscription plans
        before running ``is_coffee_product_url`` so excluded non-coffee
        products (equipment, gifts, subscriptions) can never leak past the
        stock check. Sampler/collection products are deliberately not excluded.

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

            # Keep only products in a whole-bean coffee category. Equipment,
            # gifts and non-coffee categories are dropped. Samplers/collections
            # (collections-coffee) are not excluded.
            if not COFFEE_CATEGORIES.intersection(categories):
                logger.debug(f"Skipping non-coffee product: {name}")
                continue

            # Drop recurring-delivery subscription plans.
            if SUBSCRIPTION_TOKENS and (
                any(token in product_type for token in SUBSCRIPTION_TOKENS)
                or "subscription" in name.lower()
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
