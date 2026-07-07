"""Delirante scraper implementation with AI-powered extraction."""

import logging
from pathlib import Path

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="delirante",
    display_name="Delirante",
    roaster_name="Delirante",
    website="https://cafedelirante.com.ar",
    description="Argentinian specialty coffee roaster based in Bariloche, Patagonia",
    requires_api_key=True,
    currency="ARS",
    country="Argentina",
    status="available",
)
class DeliranteScraper(BaseScraper):
    """Scraper for Delirante (cafedelirante.com.ar) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Delirante scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Delirante",
            base_url="https://cafedelirante.com.ar",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the coffee collection URLs
        """
        return [
            "https://cafedelirante.com.ar/tienda/cafe/",
        ]

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
            translate_to_english=True,
        )

    async def _extract_bean_with_ai(
        self,
        ai_extractor,
        soup: BeautifulSoup,
        product_url: str,
        use_optimized_mode: bool = False,
        translate_to_english: bool = False,
    ) -> CoffeeBean | None:
        """Extract bean with AI, preprocessing the soup to send only relevant parts.

        Strips navigation, header, footer, scripts, and other chrome from the
        page HTML before passing it to the AI extractor, keeping only the
        product content area and its surrounding context.
        """
        self._strip_page_chrome(soup)

        return await super()._extract_bean_with_ai(
            ai_extractor,
            soup,
            product_url,
            use_optimized_mode=use_optimized_mode,
            translate_to_english=translate_to_english,
        )

    def _strip_page_chrome(self, soup: BeautifulSoup) -> None:
        """Remove non-content elements from the soup in-place.

        Strips navigation, header, footer, sidebar, scripts, styles, and
        other chrome so the AI extractor only sees the relevant product content.

        Args:
            soup: BeautifulSoup object to clean
        """
        for selector in [
            "header",
            "footer",
            "nav",
            "aside",
            "script",
            "style",
            "noscript",
            "iframe",
            "svg",
            "form",
            ".nav",
            ".navbar",
            ".menu",
            ".header",
            ".footer",
            ".sidebar",
            "#header",
            "#footer",
            "#sidebar",
            ".widget",
            ".widget-area",
            ".side-widgets",
            ".comments-area",
            "#comments",
            ".related",
            ".upsells",
            ".woocommerce-tabs",
            ".product_meta",
            ".social-icons",
            ".share-icons",
            ".star-rating",
            "#reviews",
            ".wp-block-group__inner-container",
            ".wp-container",
        ]:
            for tag in soup.select(selector):
                if isinstance(tag, Tag):
                    tag.decompose()

        for tag in soup.find_all(class_=lambda x: x and isinstance(x, str) and any(
            c in x.lower() for c in ["widget", "sidebar", "footer", "header", "nav-", "menu-", "comment"]
        )):
            if isinstance(tag, Tag):
                tag.decompose()

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from store page, filtering out sold-out products.

        Args:
            store_url: URL of the store page

        Returns:
            List of product URLs (excluding sold-out products)
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        # Sold-out detection: check for "outofstock" in the product container class
        # WooCommerce/Flatsome adds an "outofstock" CSS class to the product block
        # when the product is not available.
        product_urls = []
        selectors = [
            "a.woocommerce-LoopProduct-link",
            'a[href*="/tienda/cafe/"]',
        ]

        for selector in selectors:
            links = soup.select(selector)
            if links:
                for link in links:
                    if not isinstance(link, Tag):
                        continue
                    href = link.get("href")
                    if not href or not isinstance(href, str):
                        continue

                    # Sold-out detection: check product container for outofstock class
                    product_block = link.find_parent(class_=lambda x: x and "product" in (x.lower() if x else ""))
                    if product_block and isinstance(product_block, Tag):
                        block_classes = product_block.get("class", [])
                        if isinstance(block_classes, str):
                            block_classes = [block_classes]
                        if any("outofstock" in cls.lower() for cls in block_classes if isinstance(cls, str)):
                            logger.debug(f"Skipping sold-out product: {href}")
                            continue

                    full_url = self.resolve_url(href)
                    if self.is_coffee_product_url(full_url, ["/tienda/cafe/"]):
                        product_urls.append(full_url)

                break

        seen = set()
        unique_urls = []
        for url in product_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        logger.info(f"Found {len(unique_urls)} in-stock product URLs from {store_url}")
        return unique_urls

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Postprocess extracted bean to fix currency and price scaling.

        The AI extractor sometimes guesses the wrong currency or misinterprets
        ARS prices (e.g., extracting 24 instead of 24000). This corrects both.

        Args:
            bean: Extracted CoffeeBean object

        Returns:
            Postprocessed CoffeeBean object or None
        """
        object.__setattr__(bean, "currency", "ARS")

        if bean.price is not None and bean.price < 1000:
            object.__setattr__(bean, "price", bean.price * 1000)

        if bean.price_options:
            corrected_options = []
            for option in bean.price_options:
                corrected_price = option.price * 1000 if option.price < 1000 else option.price
                corrected_options.append(option.__class__(weight=option.weight, price=corrected_price))
            object.__setattr__(bean, "price_options", corrected_options)

        return bean
