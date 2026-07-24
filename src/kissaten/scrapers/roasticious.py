"""Roasticious coffee roaster scraper implementation with AI-powered extraction."""

import logging

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="roasticious",
    display_name="Roasticious",
    roaster_name="Roasticious",
    website="https://roasticious.com",
    description="Swiss specialty coffee nano roaster (WooCommerce).",
    requires_api_key=True,
    currency="CHF",
    country="Switzerland",
    status="available",
)
class RoasticiousScraper(BaseScraper):
    """Scraper for Roasticious (roasticious.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Roasticious scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Roasticious",
            base_url="https://roasticious.com",
            rate_limit_delay=1.5,
            max_retries=3,
            timeout=30.0,
        )
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
        self._url_to_roast_options = {}

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page and narrow product detail pages to just row_1 and row_2 under div.product.

        This reduces token usage and noise by extracting only the essential
        product details and description elements.
        """
        try:
            soup = await super().fetch_page(*args, **kwargs)
            url = kwargs.get("url")
            if not url and len(args) > 0:
                url = args[0]

            # Only narrow product detail pages, leave listing/category pages untouched
            if "/product/" not in (url or ""):
                return soup

            if soup is None:
                return None

            # Look for roast profile options in the select dropdown on the product page
            select_roast = soup.find("select", id="roast") or soup.find("select", class_=lambda x: x and "roast" in x.lower())
            if select_roast:
                options = {o.get("value", "").lower() for o in select_roast.find_all("option")}
                if "filter" in options and "espresso" in options:
                    self._url_to_roast_options[url.rstrip("/")] = "Both"

            row_1 = soup.find("div", class_="et_pb_row_1_tb_body")
            row_2 = soup.find("div", class_="et_pb_row_2_tb_body")

            if row_1 or row_2:
                # Create a wrapper div to contain row_1 and row_2
                wrapper = soup.new_tag("div")
                if row_1:
                    wrapper.append(row_1)
                if row_2:
                    wrapper.append(row_2)
                logger.debug(f"Narrowed soup to row_1 and row_2 for {url}")
                return wrapper

            return soup
        except Exception as e:
            logger.error(f"Error narrowing page soup: {e}")
            return soup

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the homepage URL (all products listed on homepage)
        """
        return ["https://roasticious.com/"]

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
        )

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from store page.

        Roasticious lists all products on the homepage. We filter for:
        1. Coffee products only (product_cat-coffee class)
        2. Available products (exclude outofstock class)

        Args:
            store_url: URL of the store page

        Returns:
            List of product URLs
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        all_product_urls = []

        # Find all product containers - they have classes like:
        # product type-product post-2902 status-publish first instock product_cat-coffee ...
        product_containers = soup.find_all(
            "li",
            class_=lambda x: x and "product_cat-coffee" in x
        )

        for container in product_containers:
            # Check if product is out of stock
            container_classes = container.get("class", [])
            if "outofstock" in container_classes:
                # Skip out of stock products
                link = container.find("a", href=True)
                if link:
                    logger.debug(f"Skipping out-of-stock product: {link.get('href')}")
                continue

            # Find the product link within this container
            link = container.find("a", href=True)
            if link and "/product/" in link.get("href", ""):
                all_product_urls.append(link["href"])

        # Filter out non-coffee products using URL patterns
        excluded_products = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "brew",
            "merch",
            "apparel",
            "mug",
            "tumbler",
            "hoodie",
            "tshirt",
            "shirt",
            "cap",
            "hat",
            "bag",
            "filter",
            "aeropress",
            "v60",
            "chemex",
            "kettle",
            "grinder",
            "dripper",
            "sampler",
            "taster",
            "capsules",
            "pods",
            "drip-bag",
            "gift-voucher",
        ]

        filtered_urls = []
        for url in all_product_urls:
            url_lower = url.lower()
            if not any(ex in url_lower for ex in excluded_products):
                filtered_urls.append(url)
                logger.debug(f"Including coffee product URL: {url}")
            else:
                logger.debug(f"Excluding non-coffee product URL: {url}")

        logger.info(f"Found {len(filtered_urls)} in-stock coffee product URLs out of {len(all_product_urls)} total coffee products")
        return filtered_urls

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Post-process extracted bean to ensure correct currency and roast profile.

        Args:
            bean: Extracted CoffeeBean object

        Returns:
            CoffeeBean with currency set to CHF and roast_profile updated if applicable
        """
        bean.currency = "CHF"
        normalized_url = str(bean.url).rstrip("/")
        if normalized_url in self._url_to_roast_options:
            bean.roast_profile = self._url_to_roast_options[normalized_url]
        return bean