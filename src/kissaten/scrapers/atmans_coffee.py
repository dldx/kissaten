"""atmans Coffee scraper implementation with Shopify JSON extraction."""

import logging

from ..schemas import CoffeeBean
from .registry import register_scraper
from .shopify_base import ShopifyJsonScraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="atmans-coffee",
    display_name="atmans Coffee",
    roaster_name="atmans Coffee",
    website="https://www.atmanscoffee.com",
    description="Specialty coffee roaster based in Barcelona, Spain with curated selection focusing on POV",
    requires_api_key=True,
    currency="EUR",
    country="Spain",
    status="available",
)
class AtmansCoffeeScraper(ShopifyJsonScraper):
    """Scraper for atmans Coffee using Shopify products.json."""

    def __init__(self, api_key: str | None = None):
        """Initialize the scraper.

        Args:
            api_key: Optional API key for AI-powered extraction
        """
        super().__init__(
            roaster_name="atmans Coffee",
            base_url="https://www.atmanscoffee.com",
            products_json_urls=[
                "https://www.atmanscoffee.com/en/collections/all-coffees/products.json",
            ],
            scrape_product_pages=True,
            cache_product_pages=True,
            rate_limit_delay=1.0,
            max_retries=3,
            timeout=30.0,
            use_optimized_mode=True,
        )

        # Exclude subscription products or other non-coffee items
        self.exclude_slugs = [
            "pack-de-muestras",
            "beanz",
            "coffee-bag",
            "suscripcion-",
        ]

        if api_key:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    def preprocess_product_soup(self, soup: any) -> any:
        """Limit extraction to the <product-form> element for token efficiency."""
        product_form = soup.find("product-form")
        if product_form:
            logger.debug("Limiting extraction to <product-form> element")
            return product_form
        return soup

    async def _extract_bean_with_ai(
        self,
        ai_extractor: any,
        soup: any,
        product_url: str,
        use_optimized_mode: bool = False,
        translate_to_english: bool = True,
    ) -> CoffeeBean | None:
        """Override to ensure content is translated to English."""
        return await super()._extract_bean_with_ai(
            ai_extractor=ai_extractor,
            soup=soup,
            product_url=product_url,
            use_optimized_mode=use_optimized_mode,
            translate_to_english=True,
        )
