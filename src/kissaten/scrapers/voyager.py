"""Voyager Coffee scraper implementation with AI-powered extraction.

Voyager Coffee is a specialty coffee roaster and cafe based in Buckfastleigh,
Devon, UK, selling on a WordPress + WooCommerce storefront at
www.voyagercoffee.co.uk (canonical www host). The catalogue spans whole-bean
coffees, curated tasting packs, subscriptions, brewing equipment and wholesale
supplies.

Discovery uses the public unauthenticated WooCommerce Store API (product
listing + prices/variants + per-product categories), filtering to whole-bean
coffee in the ``coffee`` category (incl. curated sampler/tasting packs, which
are flagged ``is_tasting_kit`` rather than excluded) and dropping sold-out
items via the ``is_in_stock`` flag. Per-product bean fields (origin, process,
tasting notes, weight, etc.) come from AI extraction of each product's
JSON-LD-annotated HTML page — mirroring the the_lost_barn / santu_coffee
pattern.
"""

import json
import logging

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)

# Public WooCommerce Store API endpoint for product discovery. Returns the full
# current catalogue (whole-bean coffees, sampler packs, equipment, wholesale,
# syrups, etc.) with prices, variants, categories and canonical permalinks,
# which we filter down to whole-bean coffee (+ samplers) below. The store has
# ~280 products, so results are paginated at the Store API max of per_page=100.
STORE_API_URL = "https://www.voyagercoffee.co.uk/wp-json/wc/store/v1/products?per_page=100"

# Product category that marks a product as whole-bean coffee (or a curated
# sampler/tasting pack, which are kept and later flagged ``is_tasting_kit``).
# Voyager keeps samplers inside the ``coffee`` category rather than a separate
# sample-boxes category.
COFFEE_CATEGORY = "coffee"


@register_scraper(
    name="voyager",
    display_name="Voyager Coffee",
    roaster_name="Voyager Coffee",
    website="https://www.voyagercoffee.co.uk",
    description="Specialty coffee roaster and cafe based in Buckfastleigh, Devon, UK "
    "offering whole-bean blends and single-origin coffees plus curated "
    "tasting packs (WooCommerce storefront).",
    requires_api_key=True,
    currency="GBP",
    country="United Kingdom",
    status="available",
)
class VoyagerScraper(BaseScraper):
    """Scraper for Voyager Coffee (voyagercoffee.co.uk) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Voyager Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Voyager Coffee",
            base_url="https://www.voyagercoffee.co.uk",
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
        authoritative, current catalogue and exposes the product permalinks
        (canonical ``/product/<slug>/`` URLs) used for extraction.

        Returns:
            List containing the WooCommerce Store API URL.
        """
        return [STORE_API_URL]

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from the WooCommerce Store API.

        # Sold-out detection: API ``is_in_stock`` flag
        The Store API exposes an ``is_in_stock`` boolean per product, so no
        HTML class/text scanning is needed. The catalogue is paginated
        (per_page=100), so we walk pages until the Store API returns an empty
        page. We filter to products in the ``coffee`` category (samplers are
        kept and later flagged ``is_tasting_kit``) before running
        ``is_coffee_product_url`` so excluded non-coffee products (equipment,
        machines, syrups, disposable cups, merch) can never leak past the
        stock check.

        Args:
            store_url: URL of the WooCommerce Store API endpoint.

        Returns:
            List of whole-bean/sampler product URLs found via the API.
        """
        product_urls: list[str] = []
        page = 1

        while True:
            page_url = f"{store_url}&page={page}"
            try:
                response = await self.client.get(page_url)
                response.raise_for_status()
                products = json.loads(response.text)
            except Exception as e:
                logger.error(f"Failed to fetch Store API page {page} from {store_url}: {e}")
                if page == 1:
                    self._failed_listing_urls.append(store_url)
                return product_urls

            if not isinstance(products, list) or not products:
                if page == 1:
                    logger.error(f"Unexpected/empty Store API payload from {store_url}")
                    self._failed_listing_urls.append(store_url)
                break

            for product in products:
                # Sold-out products are not in the current catalogue.
                if product.get("is_in_stock") is False:
                    logger.debug(f"Skipping sold-out product: {product.get('name')}")
                    continue

                # Keep whole-bean coffee (and curated samplers inside the same
                # category); drop equipment, machines, subscriptions and other
                # non-coffee products.
                categories = {cat.get("slug", "") for cat in (product.get("categories") or [])}
                if COFFEE_CATEGORY not in categories:
                    logger.debug(f"Skipping non-coffee product: {product.get('name')}")
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
