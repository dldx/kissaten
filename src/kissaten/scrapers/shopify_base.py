"""Shopify JSON-based scraper base class."""

import json
import logging
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from ..schemas import CoffeeBean
from .base import BaseScraper

logger = logging.getLogger(__name__)


class ShopifyJsonScraper(BaseScraper):
    """Base class for scrapers that use Shopify's products.json endpoint.

    This scraper uses products.json for discovery and stock status, then
    uses AI extraction on the product page HTML enriched with JSON metadata.
    """

    def __init__(
        self,
        roaster_name: str,
        base_url: str,
        products_json_urls: list[str],
        scrape_product_pages: bool = True,
        cache_product_pages: bool = False,
        rate_limit_delay: float = 1.0,
        max_retries: int = 3,
        timeout: float = 30.0,
        custom_headers: dict[str, str] | None = None,
        use_optimized_mode: bool = False,
    ):
        """Initialize the Shopify JSON scraper.

        Args:
            roaster_name: Name of the roaster
            base_url: Base URL of the store
            products_json_urls: List of products.json endpoints to scrape
            rate_limit_delay: Delay between requests
            max_retries: Maximum number of retries
            timeout: Request timeout
            custom_headers: Custom HTTP headers
        """
        super().__init__(
            roaster_name=roaster_name,
            base_url=base_url,
            rate_limit_delay=rate_limit_delay,
            max_retries=max_retries,
            timeout=timeout,
            custom_headers=custom_headers,
        )
        self.products_json_urls = products_json_urls
        self.scrape_product_pages = scrape_product_pages
        self.cache_product_pages = cache_product_pages
        self.use_optimized_mode = use_optimized_mode
        self.exclude_slugs: list[str] = []  # Can be overridden by subclasses
        self._shopify_product_data: dict[str, dict[str, Any]] = {}  # URL -> product JSON
        self._shopify_stock_status: dict[str, bool] = {}  # URL -> any variant available

    async def _fetch_all_shopify_products(self, products_json_url: str) -> list[dict[str, Any]]:
        """Fetch all products from a Shopify products.json endpoint with pagination.

        Args:
            products_json_url: URL to the products.json endpoint

        Returns:
            List of product dictionaries
        """
        all_products = []
        page = 1
        limit = 250

        while True:
            url = f"{products_json_url}?limit={limit}&page={page}"
            logger.info(f"Fetching Shopify products: {url}")

            try:
                response = await self.client.get(url)
                response.raise_for_status()
                data = response.json()

                products = data.get("products", [])
                if not products:
                    break

                all_products.extend(products)
                logger.debug(f"Fetched {len(products)} products from page {page}")

                if len(products) < limit:
                    break

                page += 1
            except Exception as e:
                logger.error(f"Error fetching Shopify products from {url}: {e}")
                break

        return all_products

    async def get_store_urls(self) -> list[str]:
        """Returns the products.json URLs to scrape.

        Returns:
            List of products.json URLs
        """
        return self.products_json_urls

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from a Shopify products.json endpoint.

        Args:
            store_url: URL of the products.json endpoint

        Returns:
            List of product URLs
        """
        products = await self._fetch_all_shopify_products(store_url)
        found_urls = []

        for product in products:
            handle = product.get("handle")
            if not handle:
                continue

            # Skip explicitly excluded product slugs (matches if slug is a substring of handle)
            if any(slug in handle for slug in self.exclude_slugs):
                logger.debug(f"Skipping excluded product slug: {handle}")
                continue

            # Build product URL using the base of the products.json URL
            # This handles markets/localized paths (e.g. /en/collections/beans/products/...)
            base_path = store_url.replace("/products.json", "")
            url = f"{base_path}/products/{handle}"

            # Store metadata for later enrichment and stock status
            self._shopify_product_data[url] = product

            # A product is in stock if any of its variants are available
            is_available = any(v.get("available", False) for v in product.get("variants", []))
            self._shopify_stock_status[url] = is_available

            # Filter out non-coffee products using base class logic
            if self.is_coffee_product_url(url) and self.is_coffee_product_name(product.get("title", "")):
                found_urls.append(url)

        return found_urls

    async def create_diffjson_stock_updates(
        self, current_product_urls: list[str], output_dir: Path | None = None, force_full_update: bool = False
    ) -> tuple[int, int]:
        """Override stock updates to use accurate Shopify variant availability.

        Args:
            current_product_urls: List of URLs currently in the Shopify catalog
            output_dir: Base output directory
            force_full_update: Whether to force a full update

        Returns:
            Tuple of (in_stock_count, out_of_stock_count)
        """
        if force_full_update:
            return 0, 0

        if output_dir is None:
            output_dir = Path("data")

        # Load historical beans to know what we've seen before
        self._load_existing_beans_from_all_sessions(output_dir)

        # Products that were actually found in the catalog AND have at least one variant available
        in_stock_known = []
        for url in self._all_sessions_bean_files:
            # Check if this URL is now excluded (substring match)
            is_excluded = any(slug in url for slug in self.exclude_slugs)

            # Debug log to verify why it's not working
            if is_excluded:
                logger.info(f"Marking previously scraped but now excluded product as out-of-stock: {url}")

            if not is_excluded and url in self._shopify_stock_status and self._shopify_stock_status[url]:
                in_stock_known.append(url)

        # Create "in-stock" updates for these
        await self._create_stock_updates(in_stock_known, output_dir)

        # Everything else is considered out-of-stock (either removed from catalog or sold out)
        # We pass in_stock_known as the "current" list to the base method
        # and it will mark everything else in _all_sessions_bean_files as out-of-stock.
        await self._create_out_of_stock_updates(in_stock_known, output_dir)

        out_of_stock_count = len(self._all_sessions_bean_files) - len(in_stock_known)
        return len(in_stock_known), max(0, out_of_stock_count)

    def _format_shopify_context(self, product: dict[str, Any]) -> str:
        """Format Shopify product metadata into an HTML snippet for AI enrichment.

        Args:
            product: Shopify product dictionary

        Returns:
            HTML string containing metadata
        """
        html_parts = ["<div id=\"shopify-structured-data\" style=\"display:none;\">"]

        # Inject the raw JSON metadata as a data attribute or script tag
        # This ensures the AI has access to the exact structure from Shopify
        json_data = json.dumps(product, indent=2)
        html_parts.append("<script type=\"application/json\" id=\"shopify-product-json\">")
        html_parts.append(json_data)
        html_parts.append("</script>")

        html_parts.append("</div>")
        return "\n".join(html_parts)

    def _inject_shopify_context(self, soup: BeautifulSoup, product: dict[str, Any]) -> BeautifulSoup:
        """Inject structured Shopify metadata into the soup.

        Args:
            soup: Original BeautifulSoup object
            product: Shopify product dictionary

        Returns:
            Modified BeautifulSoup object
        """
        # Allow subclasses to pre-process the soup (e.g., remove carousels)
        # before we inject the Shopify metadata
        soup = self.preprocess_product_soup(soup)

        context_html = self._format_shopify_context(product)
        context_soup = BeautifulSoup(context_html, "lxml")
        context_div = context_soup.find("div", id="shopify-structured-data")

        if soup.body:
            # Insert at the top of the body
            soup.body.insert(0, context_div)
        else:
            # Or just append if no body
            soup.append(context_div)

        return soup

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Hook for subclasses to clean up the product page HTML before AI extraction.

        This is useful for removing large irrelevant elements like carousels,
        footers, or recommendations that might confuse the AI or waste tokens.

        Args:
            soup: Original BeautifulSoup object of the product page

        Returns:
            Modified BeautifulSoup object
        """
        return soup

    async def _extract_bean_with_ai(
        self,
        ai_extractor: Any,
        soup: BeautifulSoup,
        product_url: str,
        use_optimized_mode: bool = False,
        translate_to_english: bool = False,
    ) -> CoffeeBean | None:
        """Override to inject Shopify metadata before AI extraction."""
        url_str = str(product_url)

        if url_str in self._shopify_product_data:
            product_json = self._shopify_product_data[url_str]

            # Check if the preprocess_product_soup hook has been overridden by a subclass
            # If it is NOT overridden, it is safe to strip the full HTML in optimized mode
            is_hook_customized = type(self).preprocess_product_soup is not ShopifyJsonScraper.preprocess_product_soup

            if use_optimized_mode and not is_hook_customized:
                logger.info(f"Using Shopify JSON-only context for {url_str} in optimized mode")
                # Create a minimal soup with ONLY the Shopify JSON context
                context_html = self._format_shopify_context(product_json)
                soup = BeautifulSoup(context_html, "lxml")
            else:
                logger.info(f"Injecting Shopify metadata context for {url_str}")
                soup = self._inject_shopify_context(soup, product_json)

        return await super()._extract_bean_with_ai(
            ai_extractor=ai_extractor,
            soup=soup,
            product_url=product_url,
            use_optimized_mode=use_optimized_mode,
            translate_to_english=translate_to_english,
        )

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Override to ensure currency from Shopify metadata is used.

        Args:
            bean: Extracted CoffeeBean object

        Returns:
            Postprocessed CoffeeBean object
        """
        if self.store_currency:
            logger.info(f"Overwriting bean currency with store currency: {self.store_currency}")
            bean.currency = self.store_currency

        return super().postprocess_extracted_bean(bean)

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Override to optionally skip fetching the product page.

        If self.scrape_product_pages is False, we pass an empty soup to AI extraction.

        Args:
            product_urls: List of URLs for new products

        Returns:
            List of newly scraped CoffeeBean objects
        """
        if not product_urls:
            return []

        # We have new products to scrape, so we need currency context.
        # Fetch the collection page (products.json URL base) once to detect currency.
        # Product pages often redirect to non-localized URLs that lack Shopify.currency,
        # so we use the known localized collection URL instead.
        if not self._currency_detected and self.products_json_urls:
            collection_url = self.products_json_urls[0].replace("/products.json", "")
            try:
                logger.info(f"Fetching collection page for currency detection: {collection_url}")
                collection_soup = await self.fetch_page(collection_url)
                if collection_soup:
                    currency = self._extract_currency_from_html(collection_soup)
                    if currency:
                        self.store_currency = currency
                        self._currency_detected = True
                        logger.info(f"Detected store currency from collection page: {currency}")
            except Exception as e:
                logger.warning(f"Failed to fetch collection page for currency detection: {e}")

        if self.scrape_product_pages:
            # Standard behavior: fetch page, AI extracts with injected context
            return await super()._scrape_new_products(product_urls, use_optimized_mode=self.use_optimized_mode)

        # Optimized behavior: don't fetch page, just use JSON context
        logger.info(f"Skiping page fetch for {len(product_urls)} Shopify products - using JSON context only")
        beans = []
        for url in product_urls:
            # Optionally cache the page for documentation without using it for AI
            if self.cache_product_pages:
                logger.info(f"Caching product page for documentation: {url}")
                await self.fetch_page_with_screenshot(url, use_playwright=True)

            # We skip fetch_page entirely for AI extraction. It will work purely on injected JSON.
            # We pass an empty soup to _extract_bean_with_ai.
            empty_soup = BeautifulSoup("<html><body></body></html>", "lxml")

            bean = await self._extract_bean_with_ai(
                ai_extractor=self.ai_extractor,
                soup=empty_soup,
                product_url=url,
                use_optimized_mode=self.use_optimized_mode,
            )
            if bean:
                # Save the bean and mark as scraped
                output_dir = Path("data")
                await self.save_bean_with_image(bean, output_dir)
                self._mark_bean_as_scraped(url)
                beans.append(bean)

        return beans
