"""Flat&White scraper implementation with AI-powered extraction."""

import logging

from bs4 import BeautifulSoup, Tag

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="flat-white",
    display_name="Flat&White",
    roaster_name="Flat&White",
    website="https://flatnwhite.com",
    description="Argentinian specialty coffee roaster founded in 2016, with multiple cafés in Buenos Aires and a Diedrich roastery",
    requires_api_key=True,
    currency="ARS",
    country="Argentina",
    status="available",
)
class FlatWhiteScraper(BaseScraper):
    """Scraper for Flat&White (flatnwhite.com) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Flat&White scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Flat&White",
            base_url="https://flatnwhite.com",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the coffee collection URL
        """
        return [
            "https://flatnwhite.com/cafe-de-especialidad-flatwhite-argentina/",
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
        """Extract bean with AI, sending only the essential product data.

        Replaces the full page HTML with a minimal soup containing only:
          - <title> and key <meta> tags
          - Product text (name, price, description, variants, image URLs)
          - Schema.org JSON-LD structured data
        """
        self._minimize_soup_for_ai(soup)

        return await super()._extract_bean_with_ai(
            ai_extractor,
            soup,
            product_url,
            use_optimized_mode=use_optimized_mode,
            translate_to_english=translate_to_english,
        )

    def _minimize_soup_for_ai(self, soup: BeautifulSoup) -> None:
        """Replace the page with a minimal HTML containing only essential data."""
        essentials = []

        title = soup.find("title")
        if title:
            essentials.append(title.extract())

        for meta in soup.find_all("meta"):
            prop = meta.get("property", "") or meta.get("name", "") or ""
            if any(k in prop for k in ["og:", "twitter:"]):
                essentials.append(meta.extract())

        text_parts = []

        h1 = soup.find("h1", class_="product_title")
        if h1:
            text_parts.append(h1.get_text(" ", strip=True))

        price = soup.find(class_="price")
        if price:
            text_parts.append("Price: " + price.get_text(" ", strip=True))

        desc = soup.find(class_="woocommerce-product-details__short-description")
        if desc:
            text_parts.append(desc.get_text(" ", strip=True))

        variations = soup.find(class_="variations")
        if variations:
            text_parts.append("Variations: " + variations.get_text(" ", strip=True))

        gallery = soup.find(class_="woocommerce-product-gallery")
        if gallery:
            img_urls = []
            for img in gallery.find_all("img"):
                src = img.get("src") or img.get("data-src") or ""
                if src:
                    img_urls.append(src)
            if img_urls:
                text_parts.append("Product images: " + ", ".join(img_urls))

        for tab in soup.find_all(class_=lambda x: x and "woocommerce-Tabs-panel--description" in (x or "")):
            text_parts.append(tab.get_text(" ", strip=True))

        if text_parts:
            content_div = soup.new_tag("div", id="product-content")
            content_div.string = "\n\n".join(text_parts)
            essentials.append(content_div)

        for script in soup.find_all("script", type="application/ld+json"):
            text = script.string or ""
            if "Product" in text:
                essentials.append(script.extract())

        head = soup.find("head")
        body = soup.find("body")
        if head:
            head.clear()
        if body:
            body.clear()
        if body:
            for el in essentials:
                body.append(el)

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

        # Sold-out detection: WooCommerce adds an "outofstock" CSS class to
        # the product container when the product is not available.
        product_urls = []
        selectors = [
            "a.woocommerce-LoopProduct-link",
            "a.woocommerce-loop-product__link",
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
                    product_block = link.find_parent(
                        class_=lambda x: x and "product" in (x.lower().split() if x else [])
                    )
                    if product_block and isinstance(product_block, Tag):
                        block_classes = product_block.get("class", [])
                        if isinstance(block_classes, str):
                            block_classes = [block_classes]
                        if any("outofstock" in cls.lower() for cls in block_classes if isinstance(cls, str)):
                            logger.debug(f"Skipping sold-out product: {href}")
                            continue

                    full_url = self.resolve_url(href)
                    if self.is_coffee_product_url(full_url, ["/cafe-de-especialidad", "/cafe-especialidad"]):
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
