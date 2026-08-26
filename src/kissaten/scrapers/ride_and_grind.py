"""Ride and Grind scraper implementation with AI-powered extraction.

Ride and Grind (ridegrind.com, the live successor of the formerly-parked
rideandgrind.co.uk) is a Wallyford, East Lothian (Unit 1E Wallyford Industrial
Estate) roaster selling on a WordPress + WooCommerce storefront at
www.ridegrind.com. The catalogue is whole-bean coffee split across two
categories (``coffee-tins`` and ``coffee-bags``) plus accessories, pods,
apparel, gift subscriptions and gift cards.

Discovery uses the public unauthenticated WooCommerce Store API (product
listing + prices/variants + per-product categories), filtering to whole-bean
coffee in the tins/bags categories and dropping pods, subscriptions and
non-coffee merch. Per-product bean fields (origin, process, tasting notes,
weight, etc.) come from AI extraction of each product's JSON-LD-annotated HTML
page — mirroring the the_roasting_project / the_lost_barn pattern.
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
# current catalogue (whole-bean coffees, pods, accessories, apparel, gift
# subscriptions/cards) with prices, variants, categories and canonical
# permalinks, which we filter down to whole-bean coffee below.
STORE_API_URL = "https://www.ridegrind.com/wp-json/wc/store/v1/products?per_page=100"

# Categories that mark a product as whole-bean coffee. Products in either of
# these are the coffee catalogue (17 tins + 11 bags in the current store).
COFFEE_CATEGORIES = {"coffee-tins", "coffee-bags"}

# Pods are not whole-bean coffee and are explicitly excluded, even though the
# single "Coffee Pods (Nespresso)" product also carries the tins/bags
# categories. Samplers/tasting kits (e.g. "Favourites Tasting Pack") are
# intentionally NOT excluded here so they land in the admin review queue.
POD_CATEGORY = "coffee-pods"

# Recurring-delivery subscription plans (e.g. "New Coffee Every Time (Bag
# Subscription)") are excluded. The whole-bean names never contain this.
SUBSCRIPTION_NAME_RE = re.compile(r"\b(?:subscription)\b", re.IGNORECASE)


@register_scraper(
    name="ride-and-grind",
    display_name="Ride and Grind",
    roaster_name="Ride and Grind",
    website="https://www.ridegrind.com",
    description="Wallyford, East Lothian roaster (Unit 1E Wallyford Industrial "
    "Estate) offering whole-bean blends and single-origin coffees in tins and "
    "re-fill bags (WooCommerce storefront).",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class RideAndGrindScraper(BaseScraper):
    """Scraper for Ride and Grind (ridegrind.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Ride and Grind scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Ride and Grind",
            base_url="https://www.ridegrind.com",
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
        ``coffee-tins``/``coffee-bags`` categories, drop pods and subscription
        plans before running ``is_coffee_product_url`` so excluded products
        (pods, accessories, apparel, gift subscriptions/cards) can never leak
        past the stock check. Sampler/tasting-kit products are deliberately not
        excluded.

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

            # Keep only whole-bean coffee (tins/bags). Accessories, apparel,
            # gift subscriptions and gift cards are in other categories and are
            # dropped here. Samplers are not excluded.
            if not categories.intersection(COFFEE_CATEGORIES):
                logger.debug(f"Skipping non-coffee product: {name}")
                continue

            # Drop coffee pods, which are not whole-bean coffee even though the
            # single Nespresso-pod product also carries the tins/bags categories.
            if POD_CATEGORY in categories:
                logger.debug(f"Skipping pod product: {name}")
                continue

            # Drop recurring-delivery subscription plans.
            if "subscription" in product_type or SUBSCRIPTION_NAME_RE.search(name):
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
