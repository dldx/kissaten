"""Kafferäven scraper implementation with Shopify JSON extraction."""

import logging
from typing import Any

from bs4 import BeautifulSoup, Tag

from ..schemas import CoffeeBean
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="kafferaven",
    display_name="Kafferäven",
    roaster_name="Kafferäven",
    website="https://www.kafferaven.se",
    description="Swedish specialty coffee roaster based in Gothenburg, roasting organic single-origin coffees with a focus on traceability and long-term producer relationships",
    requires_api_key=True,
    currency="SEK",
    country="Sweden",
    status="available",
)
class KafferavenScraper(ShopifyJsonScraper):
    """Scraper for Kafferäven (kafferaven.se) using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize Kafferäven scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Kafferäven",
            base_url="https://www.kafferaven.se",
            products_json_urls=[
                "https://www.kafferaven.se/collections/kaffebonor/products.json",
            ],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=False,
        )

        # Exclude non-coffee products (subscriptions, gift cards, equipment, etc.)
        self.exclude_slugs = [
            "subscription",
            "gift-card",
            "gift",
            "wholesale",
            "equipment",
            "brewing",
            "accessory",
            "merchandise",
            "sampler",
            "taster-pack",
            "apparel",
            "mug",
            "tumbler",
            "hoodie",
            "tshirt",
            "capsules",
            "pods",
            "cold-brew-cans",
            "easy-pour",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup | Tag:
        """Limit extraction to the main product section.

        Kafferäven's product page renders accordions (OM PRODUCENTEN, OM
        SMAKKATEGORIERNA, FRAKT) but the content is already present in the DOM
        inside <div class="product__accordion__inner" data-collapsible-content>;
        only the wrapping button is toggled visually. The page also includes
        a structured metadata paragraph with SMAKKATEGORI / LAND / REGION /
        VÄXTHÖJD / BÖNTYP / PROCESS / PRODUCENT / RELATION that lives next
        to the description. Both blocks are highly relevant for AI extraction.

        The rest of the page (header, announcement bar, related products,
        cross-sell image+text blocks, footer, etc.) is dropped to save tokens.
        """
        main = soup.find("main", id="MainContent")
        if not main:
            return soup

        # Drop noisy sections inside <main>: marquees, related products,
        # image-with-text cross-sells, generic accordions (FAQ-like blocks
        # unrelated to the product). The product section is identified by the
        # `data-section-type="product-template"` flag on the inner <section>.
        product_wrapper = None
        for wrapper in main.find_all("div", class_="shopify-section"):
            inner_section_type = ""
            inner = wrapper.find(attrs={"data-section-type": True})
            if inner is not None:
                inner_section_type = inner.get("data-section-type", "")
            if inner_section_type == "product-template":
                product_wrapper = wrapper
            else:
                wrapper.decompose()

        if product_wrapper is None:
            return soup

        # Build a new soup containing only the product section.
        new_body = BeautifulSoup("<body></body>", "lxml")
        new_body.append(product_wrapper.__copy__())
        return new_body

    def _get_roaster_dir_name(self) -> str:
        """Override to keep the data/roasters folder name as 'kafferaven'.

        The base implementation strips 'ä' to '_' (giving 'kaffer_ven'), but
        the historical directory convention here is 'kafferaven'.
        """
        return "kafferaven"

    async def _extract_bean_with_ai(
        self,
        ai_extractor: Any,
        soup: BeautifulSoup,
        product_url: str,
        use_optimized_mode: bool = False,
        translate_to_english: bool = True,
    ) -> CoffeeBean | None:
        """Override to ensure Swedish content is translated to English."""
        return await super()._extract_bean_with_ai(
            ai_extractor=ai_extractor,
            soup=soup,
            product_url=product_url,
            use_optimized_mode=use_optimized_mode,
            translate_to_english=True,  # Always translate Swedish to English
        )