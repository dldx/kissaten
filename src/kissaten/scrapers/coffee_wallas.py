"""Coffee Wallas scraper implementation with Shopify JSON enrichment."""

import logging
from typing import Any

from bs4 import BeautifulSoup, Tag

from ..schemas import CoffeeBean
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="coffee-wallas",
    display_name="Coffee Wallas",
    roaster_name="Coffee Wallas",
    website="https://coffeewallas.com",
    description="Canadian specialty coffee roaster focusing on Asian coffee origins",
    requires_api_key=True,
    currency="CAD",
    country="Canada",
    status="available",
)
class CoffeeWallasScraper(ShopifyJsonScraper):
    """Scraper for Coffee Wallas (coffeewallas.com) using Shopify JSON enrichment."""

    def __init__(self, api_key: str | None = None):
        """Initialize Coffee Wallas scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Coffee Wallas",
            base_url="https://coffeewallas.com",
            products_json_urls=["https://coffeewallas.com/collections/frontpage/products.json"],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude non-coffee products
        self.exclude_slugs = [
            "gift-card",
            "subscription",
            "will-it-blend-",
            "merch",
            "wholesale",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_url(self, url: str) -> str:
        """Preprocess product URL to remove collection segments and ensure canonical format."""
        # Standardize Shopify URL by removing collection segments
        # e.g. /collections/frontpage/products/india -> /products/india
        if "/collections/" in url and "/products/" in url:
            parts = url.split("/products/")
            if len(parts) > 1:
                return f"{self.base_url}/products/{parts[1]}"
        return url

    async def _extract_bean_with_ai(
        self,
        ai_extractor: Any,
        soup: BeautifulSoup,
        product_url: str,
        use_optimized_mode: bool = False,
        translate_to_english: bool = False,
    ) -> CoffeeBean | None:
        """Override to use the coffee label image instead of a page screenshot."""
        # Get correctly detected store currency
        if not self._currency_detected:
            page_currency = self._extract_currency_from_html(soup)
            if page_currency:
                self.store_currency = page_currency
                self._currency_detected = True
        page_currency = self.store_currency

        # Find the label image URL from our context
        label_div = soup.find("div", id="coffee-label-images")
        label_url = None
        if isinstance(label_div, Tag):
            img = label_div.find("img", {"data-type": "coffee-label"})
            if isinstance(img, Tag):
                label_url = str(img.get("src", ""))

        screenshot_bytes = None
        if label_url:
            logger.info(f"Downloading label image for visual AI analysis: {label_url}")
            try:
                response = await self.client.get(label_url)
                response.raise_for_status()
                screenshot_bytes = response.content
            except Exception as e:
                logger.warning(f"Failed to download label image {label_url}: {e}")

        # If no label image was found/downloaded, fall back to standard page screenshot
        # ONLY if use_optimized_mode is True, otherwise BaseScraper logic applies.
        if not screenshot_bytes and use_optimized_mode:
            screenshot_bytes = await self.take_screenshot(product_url)

        # Build augmented soup (metadata + html)
        if product_url in self._shopify_product_data:
            product_json = self._shopify_product_data[product_url]
            soup = self._inject_shopify_context(soup, product_json)

        # Call AI extractor with label image (passed as screenshot_bytes)
        bean = await ai_extractor.extract_coffee_data(
            str(soup),
            product_url,
            screenshot_bytes=screenshot_bytes,
            use_optimized_mode=True,  # Force optimized mode to ensure screenshot_bytes is used
            default_currency=page_currency,
        )

        if bean:
            bean.roaster = self.roaster_name
            return self.postprocess_extracted_bean(bean)

        return None

    def _format_shopify_context(self, product: dict[str, Any]) -> str:
        """Inject Shopify metadata and labels image URL for AI extraction."""
        html_parts = [super()._format_shopify_context(product)]

        # Extract labels image from Shopify images (usually the one with "Label" in filename)
        images = product.get("images", [])
        label_images = [
            str(img["src"])
            for img in images
            if "label" in str(img.get("src", "")).lower() or "website" in str(img.get("src", "")).lower()
        ]

        if label_images:
            # We add a hidden section specifically for the label image URL
            # so the AI can see it as part of the structured context
            html_parts.append('<div id="coffee-label-images" style="display:none;">')
            for img_url in label_images:
                html_parts.append(f'<img src="{img_url}" data-type="coffee-label" />')
            html_parts.append("</div>")

        return "\n".join(html_parts)
