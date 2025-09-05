"""Blue Bottle Coffee Japan scraper implementation with AI-powered extraction."""

import logging

from bs4 import BeautifulSoup

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="blue-bottle",
    display_name="Blue Bottle Coffee",
    roaster_name="Blue Bottle Coffee",
    website="https://store.bluebottlecoffee.jp",
    description="Premium specialty coffee roasters from California with Japan operations",
    requires_api_key=True,
    currency="JPY",
    country="Japan",
    status="available",
)
class BlueBottleCoffeeScraper(BaseScraper):
    """Scraper for Blue Bottle Coffee Japan (store.bluebottlecoffee.jp) with AI-powered extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Blue Bottle Coffee scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Blue Bottle Coffee",
            base_url="https://store.bluebottlecoffee.jp",
            rate_limit_delay=2.0,  # Be respectful with rate limiting
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Returns:
            List containing the main collection URLs with pagination
        """
        return [
            "https://store.bluebottlecoffee.jp/collections/blend",
            "https://store.bluebottlecoffee.jp/collections/single-origin",
            # Add more pages if needed - they show 24 products per page, total 38 products
        ]

    async def scrape(self) -> list[CoffeeBean]:
        """Scrape coffee beans from Blue Bottle Coffee using AI extraction.

        Returns:
            List of CoffeeBean objects
        """
        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=self._extract_product_urls_from_store,
            ai_extractor=self.ai_extractor,
            use_playwright=True,  # Use playwright for better JS support
            translate_to_english=True,  # Japanese site, translate to English
        )

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract product URLs from store page.

        Args:
            store_url: URL of the store page

        Returns:
            List of product URLs
        """
        soup = await self.fetch_page(store_url, use_playwright=False)
        if not soup:
            return []

        # Custom selectors for Blue Bottle Coffee store
        custom_selectors = [
            'a[href*="/products/"]',
            ".product-item-link",
            ".product-link",
            "h3 > a",  # Product titles that are links
            ".grid-product__title a",  # Common pattern
        ]

        product_urls = self.extract_product_urls_from_soup(
            soup,
            url_path_patterns=["/products/"],
            selectors=custom_selectors,
        )

        # Filter out non-coffee products
        filtered_urls = []
        for url in product_urls:
            if self._is_coffee_product_url(url):
                filtered_urls.append(url)

        return filtered_urls

    async def _extract_bean_with_ai(
        self, ai_extractor, soup: BeautifulSoup, product_url: str, use_optimized_mode: bool = False,
        translate_to_english: bool = True,
    ) -> CoffeeBean | None:
        """Extract coffee bean data using AI, focusing on div.Product.Product--large element.

        Args:
            ai_extractor: AI extractor instance
            soup: BeautifulSoup object of the product page
            product_url: URL of the product page
            use_optimized_mode: Whether to use optimized mode (with screenshots)

        Returns:
            CoffeeBean object or None if extraction fails
        """
        try:
            # Focus on the div.Product.Product--large element as requested
            def has_product_classes(css_class):
                if css_class:
                    classes = css_class if isinstance(css_class, list) else css_class.split()
                    return "Product" in classes and "Product--large" in classes
                return False

            product_div = soup.find("section", class_=has_product_classes)
            if product_div:
                # Create a new soup object with just the product div content
                limited_soup = BeautifulSoup(str(product_div), 'html.parser')
                logger.debug(f"Limiting extraction to section.Product.Product--large for {product_url}")
                html_content = str(limited_soup)
            else:
                # Fallback to full page if the specific div is not found
                logger.warning(f"section.Product.Product--large not found for {product_url}, using full page")
                html_content = str(soup)

            # Use the AI extractor
            bean: CoffeeBean = await ai_extractor.extract_coffee_data(
                html_content=html_content,
                product_url=product_url,
                use_optimized_mode=use_optimized_mode,
            )
            if bean:
                logger.debug(f"AI extracted: {bean.name} from {', '.join(str(origin) for origin in bean.origins)}")
                if translate_to_english:
                    bean = await ai_extractor.translate_to_english(bean)
                return bean

        except Exception as e:
            logger.error(f"AI extraction failed for {product_url}: {e}")
            return None

    def _is_coffee_product_url(self, url: str) -> bool:
        """Filter out non-coffee products by URL.

        Args:
            url: Product URL to check

        Returns:
            True if this appears to be a coffee product URL
        """
        # Exclude equipment, merchandise, and other non-coffee items
        excluded_patterns = [
            'dripper',  # ドリッパー
            'filter',   # フィルター
            'mill',     # ミル
            'grinder',  # グラインダー
            'mug',      # マグ
            'cup',      # カップ
            'glass',    # グラス
            'tumbler',  # タンブラー
            'kit',      # キット (brewing kits)
            'starter',  # スターターキット
            'equipment',
            'brewing',
            'accessories',
            'merchandise',
            'apparel',
            'shirt',
            'tote',
            'bag',
            'subscription',
            'granola',  # グラノーラ
        ]

        url_lower = url.lower()
        return not any(pattern in url_lower for pattern in excluded_patterns)

    def _is_coffee_product_name(self, name: str) -> bool:
        """Filter out non-coffee products by name.

        Args:
            name: Product name to check

        Returns:
            True if this appears to be a coffee product
        """
        # Additional name-based filtering for Japanese products
        excluded_name_patterns = [
            'ドリッパー',  # dripper
            'フィルター',  # filter
            'ミル',      # mill
            'グラインダー', # grinder
            'マグ',      # mug
            'カップ',     # cup
            'グラス',     # glass
            'タンブラー',  # tumbler
            'キット',     # kit
            'スターター',  # starter
            'グラノーラ',  # granola
            'セット',     # set (unless it's coffee set)
        ]

        name_lower = name.lower()

        # Allow coffee sets but exclude other equipment sets
        if 'セット' in name_lower:
            coffee_indicators = ['コーヒー', 'ブレンド', 'アフリカ', 'インスタント']
            has_coffee_indicator = any(indicator in name_lower for indicator in coffee_indicators)
            if not has_coffee_indicator:
                return False

        return not any(pattern in name_lower for pattern in excluded_name_patterns)
