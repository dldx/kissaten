"""Scraper for Coffee Lab (coffeelab.pl) - Polish specialty coffee roaster."""

import logging

from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="coffeelab",
    display_name="Coffee Lab",
    roaster_name="Coffee Lab",
    website="https://coffeelab.pl",
    description="Specialty coffee roaster from Warsaw, Poland focusing on quality and precision",
    requires_api_key=True,  # Use AI extraction for best results
    currency="PLN",
    country="Poland",
    status="available",
)
class CoffeeLabScraper(BaseScraper):
    """Scraper for Coffee Lab - Polish specialty coffee roaster."""

    def __init__(self, api_key: str | None = None):
        """Initialize the scraper.

        Args:
            api_key: Optional API key for AI-powered extraction
        """
        super().__init__(
            roaster_name="Coffee Lab",
            base_url="https://coffeelab.pl",
            rate_limit_delay=1.5,  # Be respectful to the site
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor (recommended for this site)
        self.ai_extractor = None
        try:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
        except ImportError:
            logger.warning("AI extractor not available - falling back to traditional extraction")

    def _get_excluded_url_patterns(self) -> list[str]:
        """Return base excluded URL patterns plus Coffee Lab tasting-set product slugs.

        BREWLAB sets (Polish "zestaw" = set/kit) are tasting boxes, not coffee
        beans - their product URLs contain "zestaw-brewlab".
        """
        return super()._get_excluded_url_patterns() + ["zestaw-brewlab"]

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Coffee Lab moved from PrestaShop to WooCommerce. Products are listed
        under the ``coffee-en`` product category at ``/en/product-cat/`` and
        paginated with WooCommerce-style ``/page/N/`` paths.

        Returns:
            List containing the store URLs to scrape
        """
        return [
            # Main coffee category (WooCommerce, page 1)
            "https://coffeelab.pl/en/product-cat/coffee-en/",
            # Page 2 of the coffee category
            "https://coffeelab.pl/en/product-cat/coffee-en/page/2/",
            # The coffee-en category includes all coffee subcategories
            # (espresso, filter, decaf, cascara, brewlab, magic beans)
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

        # Use the base class method with Coffee Lab specific patterns
        return self.extract_product_urls_from_soup(
            soup,
            # Coffee Lab URL patterns - WooCommerce products live under /en/product/
            url_path_patterns=[
                "/en/product/",
            ],
            selectors=[
                # WooCommerce product cards (server-rendered <li class="product">)
                "li.product a",
                "a.product-card__body",
                # Fallback selectors
                'a[href*="/en/product/"]',
                ".product-item a",
                "a.product-link",
            ],
        )
