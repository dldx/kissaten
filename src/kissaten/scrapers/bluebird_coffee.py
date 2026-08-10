"""Bluebird Coffee Roastery scraper implementation with AI-powered extraction."""

import logging

from bs4 import BeautifulSoup

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="bluebird-coffee",
    display_name="Bluebird Coffee Roastery",
    roaster_name="Bluebird Coffee Roastery",
    website="https://www.bluebirdcoffeeroastery.co.za",
    description="South African specialty coffee roaster offering single origins and blends",
    requires_api_key=True,
    currency="ZAR",
    country="South Africa",
    status="available",
)
class BluebirdCoffeeScraper(BaseScraper):
    """Scraper for Bluebird Coffee Roastery (bluebirdcoffeeroastery.co.za) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Bluebird Coffee Roastery scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Bluebird Coffee Roastery",
            base_url="https://www.bluebirdcoffeeroastery.co.za",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the coffee collection URLs
        """
        return [
            "https://www.bluebirdcoffeeroastery.co.za/product-tag/single-origin/",
            "https://www.bluebirdcoffeeroastery.co.za/special-releases/",
            "https://www.bluebirdcoffeeroastery.co.za/product-tag/espresso-blend/",
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
            use_playwright=True,
            use_optimized_mode=True,
        )

    async def _extract_bean_with_ai(
        self,
        ai_extractor,
        soup: BeautifulSoup,
        product_url: str,
        use_optimized_mode: bool = False,
        translate_to_english: bool = False,
    ) -> CoffeeBean | None:
        """Run the shared AI extraction on a soup limited to the product info.

        The shared flow serializes ``str(soup)`` and sends it to the model,
        so we prune Bluebird's Elementor megapage before delegating (see
        :meth:`preprocess_product_soup`).
        """
        soup = self.preprocess_product_soup(soup)
        return await super()._extract_bean_with_ai(
            ai_extractor,
            soup,
            product_url,
            use_optimized_mode=use_optimized_mode,
            translate_to_english=translate_to_english,
        )

    def preprocess_product_soup(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Limit the product page soup to Bluebird's product-info sections.

        Bluebird's product pages run an Elementor WooCommerce template
        (``div.elementor-location-single.product``). Every page is the same
        8-section layout, but only the first sections are product-specific:

          * summary - breadcrumb, country, title, process, price range,
            tasting notes, bag-size/grind variation controls, add-to-cart
          * spec table - origin, variety, region, producer, altitude, process
          * "Coffee Origins" description prose

        The remaining sections repeat verbatim on every product page (brew
        recipe, "Coffee at its best", FAQ, "Subscribe, and save") or are the
        related-products carousel ("More coffees you may enjoy" - roughly
        100 KB of *other* products' cards). Sending all of that to the model
        burns tokens without adding facts about this product, so we keep only
        the product-specific sections and strip markup that carries no
        information. If the theme changes and no product container is found,
        we fall back to the full page so extraction never silently loses data.
        """
        prod = soup.select_one(".elementor-location-single.product")
        if prod is not None:
            keep = [
                sec
                for sec in prod.find_all("section", recursive=False)
                if not self._is_boilerplate_section(sec)
            ]
            if not keep:
                logger.debug("No product-info sections found; sending full product page soup.")
                return soup
        else:
            prod = soup.select_one("div.product")
            if prod is None:
                logger.debug("No product container found; sending full product page soup.")
                return soup
            # Non-Elementor fallback: standard WooCommerce product containers.
            keep = prod.select(
                ".summary.entry-summary, "
                ".woocommerce-product-details__short-description, "
                ".woocommerce-tabs, "
                ".product_meta"
            )
            if not keep:
                logger.debug("No product-info containers found; sending full product page soup.")
                return soup

        limited = BeautifulSoup("<html><body></body></html>", "lxml")
        for el in keep:
            limited.body.append(el)
        self._prune_soup_for_ai(limited)
        logger.debug(f"Sending product page soup limited to {len(keep)} product-info container(s).")
        return limited

    def _is_boilerplate_section(self, section: BeautifulSoup) -> bool:
        """Return True for sections that repeat on every product page.

        These contribute only noise to the model: the recipe card, the
        "Coffee at its best" blurb, the FAQ accordion, the subscription
        pitch, and the related-products carousel.
        """
        text = " ".join(section.get_text(" ", strip=True).split())
        if not text:
            return False
        if "More coffees you may enjoy" in text or section.select_one(".related"):
            return True
        if text.startswith(
            (
                "Recipe April Plastic Brewer",
                "Coffee at its best",
                "FAQs What is the best brew method",
            )
        ):
            return True
        if "Subscribe, and save" in text[:200]:
            return True
        return False

    def _prune_soup_for_ai(self, soup: BeautifulSoup) -> None:
        """Remove markup that adds size but no bean facts.

        Elementor ships long ``data-*``/``class`` attribute strings, inline
        scripts and SVG icons. The model only needs the text and nesting:
        attributes are stripped, images collapse to their alt text, hidden
        containers and empty wrappers are dropped. Unlike the Shopify
        scrapers, "Add to cart" buttons, labels and variation selects are
        kept - they carry the availability and weight/grind facts that the
        extractor needs (Bluebird does not inject JSON variant data).
        """
        # 1) Pure-markup / non-visual elements.
        for name in (
            "script",
            "style",
            "noscript",
            "template",
            "link",
            "meta",
            "svg",
            "path",
            "circle",
            "iframe",
            "source",
            "picture",
        ):
            for tag in soup.find_all(name):
                tag.decompose()

        # 2) Hidden containers (JS mirror of variant data / popup chrome).
        for tag in soup.find_all(True):
            style = tag.get("style") or ""
            if "display:none" in style.replace(" ", ""):
                tag.decompose()

        # 3) Form inputs carry no text facts (quantity, hidden CSRF fields).
        for tag in soup.find_all("input"):
            tag.decompose()

        # 4) Collapse images to their alt text; drop images without alt.
        for img in soup.find_all("img"):
            alt = img.get("alt") or ""
            if alt:
                img.replace_with(soup.new_string(f"[image: {alt}]"))
            else:
                img.decompose()

        # 5) Elementor attribute noise: the model needs text + nesting only.
        for tag in soup.find_all(True):
            tag.attrs.clear()

        # 6) Collapse now-empty wrappers.
        changed = True
        while changed:
            changed = False
            for tag in soup.find_all(True):
                if tag.name in (
                    "html",
                    "head",
                    "body",
                    "section",
                    "div",
                    "span",
                    "p",
                    "ul",
                    "li",
                    "a",
                    "table",
                    "tbody",
                    "tr",
                    "td",
                    "th",
                    "form",
                ):
                    if not tag.get_text(strip=True) and not tag.find("img"):
                        tag.decompose()
                        changed = True

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from store page.

        Args:
            store_url: URL of the store page

        Returns:
            List of product URLs
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        # Get all product URLs using the base class method
        product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/product/"],
            selectors=[
                # WooCommerce product link selectors
                'a[href*="/product/"]',
                '.woocommerce-LoopProduct-link',
                '.product-item a',
                '.product-link',
                '.wc-block-grid__product a',
                # Bluebird specific selectors based on HTML structure
                '.product a',
                '.product-wrapper a',
            ],
        )

        # Filter out excluded products (subscriptions and non-coffee items)
        excluded_products = [
            "subscription",  # Coffee subscriptions
            "coffee-subscription",  # Coffee subscriptions
            "house-blend-subscription",  # Espresso blend subscriptions
            "bluebird-reusable-cup",
            "minimalist-wine",
            "bluebird-bag",
        ]

        filtered_urls = []
        for url in product_urls:
            if url and isinstance(url, str) and not any(excluded in url for excluded in excluded_products):
                filtered_urls.append(url)

        return filtered_urls
