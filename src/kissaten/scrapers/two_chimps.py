"""Two Chimps Coffee scraper implementation with AI-powered extraction.

Two Chimps Coffee is a small-batch specialty coffee roaster based in Oakham,
Rutland (3a 51 Pillings Road), selling on a WordPress + WooCommerce storefront
at twochimpscoffee.com (non-www canonical host). The coffee catalogue is a small
set of whole-bean coffees (single-origins, blends, limited editions, plus a
monthly special and mystery coffees), alongside per-coffee sample packs and a
large gifts / accessories / merchandise / tea section that is not coffee.

Discovery uses the public unauthenticated WooCommerce Store API (product
listing + prices/variants + per-product categories), filtering to whole-bean
coffee (``caffeinated`` / ``decaffeinated-coffee`` / ``limited-edition-coffees``
/ ``mystery-coffees``) and curated ``coffee-samples`` tasting packs, while
dropping ready-to-drink cold brew, subscriptions and everything else.
Per-product bean fields (origin, process, tasting notes, weight, etc.) come from
AI extraction of each product's HTML page — mirroring the the_lost_barn /
the_roasting_project pattern. Product permalinks are canonical
``/shop/<slug>/`` URLs.
"""

import json
import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)

# Public WooCommerce Store API endpoint for product discovery. Returns the full
# current catalogue (whole-bean coffees, samplers, gifts, accessories, tea,
# subscriptions) with prices, variants, categories and canonical permalinks,
# which we filter down to whole-bean coffee + sampler packs below.
STORE_API_URL = "https://twochimpscoffee.com/wp-json/wc/store/v1/products?per_page=100"

# Product categories that mark a product as whole-bean coffee. The roaster's
# coffee range (coffee-one..coffee-nine, half-caff, mystery coffees, monthly
# special, limited editions) all live in these categories.
BEAN_CATEGORIES = {
    "caffeinated",
    "decaffeinated-coffee",
    "limited-edition-coffees",
    "mystery-coffees",
}

# Curated sampler/tasting packs ("<coffee>-sample") land here. They are kept
# (flagged ``is_tasting_kit``) rather than excluded, per the kit-review
# pipeline, so they reach the admin review queue instead of being dropped.
SAMPLER_CATEGORY = "coffee-samples"

# Ready-to-drink canned cold brew is categorised under "caffeinated" alongside
# the whole-bean coffees, but it is not a whole-bean product and must be
# dropped. The sample packs are NOT listed here so they are kept.
NON_BEAN_CATEGORIES = {"cold-brew"}


@register_scraper(
    name="two-chimps",
    display_name="Two Chimps Coffee",
    roaster_name="Two Chimps Coffee",
    website="https://twochimpscoffee.com",
    description="Small-batch specialty roaster in Oakham, Rutland (3a 51 Pillings Road) "
    "offering whole-bean blends, single-origins, limited editions and monthly "
    "specials plus curated per-coffee sample packs (WooCommerce storefront).",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class TwoChimpsScraper(BaseScraper):
    """Scraper for Two Chimps Coffee (twochimpscoffee.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Two Chimps Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Two Chimps Coffee",
            base_url="https://twochimpscoffee.com",
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
        permalinks (canonical ``/shop/<slug>/`` URLs) used for extraction.

        Returns:
            List containing the WooCommerce Store API URL.
        """
        return [STORE_API_URL]

    async def _fetch_store_page(self, store_url: str) -> list | None:
        """Fetch and parse one page of Store API products.

        Args:
            store_url: URL of the WooCommerce Store API page endpoint.

        Returns:
            List of products, or None if the fetch/parse failed.
        """
        response = await self.client.get(store_url)
        response.raise_for_status()
        try:
            products = json.loads(response.text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Store API JSON from {store_url}: {e}")
            return None

        if not isinstance(products, list):
            logger.error(f"Unexpected Store API payload (expected a list) from {store_url}")
            return None
        return products

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from the WooCommerce Store API.

        # Sold-out detection: API ``is_in_stock`` flag
        The Store API exposes an ``is_in_stock`` boolean per product, so no
        HTML class/text scanning is needed. The catalogue spans multiple pages
        (the roaster lists gifts/tea/accessories alongside coffee, ~180
        products), so pages are followed while each returns a full
        ``per_page`` batch. We filter to whole-bean coffee (``caffeinated`` /
        ``decaffeinated-coffee`` / ``limited-edition-coffees`` /
        ``mystery-coffees``) and the ``coffee-samples`` tasting-pack category,
        dropping ready-to-drink cold brew and subscriptions before running
        ``is_coffee_product_url`` so excluded non-coffee products can never
        leak past the stock check. Sampler packs are intentionally kept.

        Args:
            store_url: URL of the WooCommerce Store API endpoint.

        Returns:
            List of whole-bean/sampler product URLs found via the API.
        """
        product_urls: list[str] = []

        page = 1
        while True:
            page_url = f"{store_url}&page={page}"
            products = await self._fetch_store_page(page_url)
            if products is None:
                # Record the failure once (the base listing URL), not per page.
                if page == 1:
                    self._failed_listing_urls.append(store_url)
                    logger.error(f"Failed to parse Store API JSON from {store_url}")
                break

            for product in products:
                # Sold-out products are not in the current catalogue.
                if product.get("is_in_stock") is False:
                    logger.debug(f"Skipping sold-out product: {product.get('name')}")
                    continue

                # Drop recurring-delivery subscription plans (incl. variable-subscription).
                product_type = (product.get("type") or "").lower()
                if "subscription" in product_type:
                    logger.debug(f"Skipping subscription product: {product.get('name')}")
                    continue

                categories = {cat.get("slug", "") for cat in (product.get("categories") or [])}

                # Ready-to-drink cold brew shares the whole-bean categories but is
                # not a whole-bean product, so it is explicitly dropped.
                if categories & NON_BEAN_CATEGORIES:
                    logger.debug(f"Skipping non-bean product: {product.get('name')}")
                    continue

                # Keep whole-bean coffee and sampler-pack products. Samplers are
                # intentionally kept (they are later flagged is_tasting_kit).
                if not (categories & BEAN_CATEGORIES) and SAMPLER_CATEGORY not in categories:
                    logger.debug(f"Skipping non-coffee product: {product.get('name')}")
                    continue

                href = product.get("permalink")
                if not isinstance(href, str) or not href:
                    continue

                full_url = self.resolve_url(href)
                # Strip query string before checking/adding to database.
                if "?" in full_url:
                    full_url = full_url.split("?")[0]

                if self.is_coffee_product_url(full_url, required_path_patterns=["/shop/"]):
                    product_urls.append(full_url)

            # Store API caps per_page at 100; a short page ends the catalogue.
            if len(products) < 100:
                break
            page += 1

        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_urls: list[str] = []
        for url in product_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        logger.info(f"Found {len(unique_urls)} product URLs from Store API (whole-bean + samplers, in-stock)")
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
