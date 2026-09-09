"""Roast Republik (Roast and Grind Africa Ltd) scraper implementation with AI-powered extraction.

Roast Republik is the specialty-coffee brand of Roast and Grind Africa Ltd, a
Kenyan roastery/coffee academy based in Nakuru (Nakuru/Nairobi Main Highway).
Their storefront runs on Zoho Commerce at https://www.kenyan-coffee.com.

Site notes discovered during research (2026-09):
- Platform is Zoho Commerce (not Shopify) — no products.json endpoint. An
  unlaunched, password-protected Shopify store exists at
  roast-republik.myshopify.com but serves no products.
- Zoho's ``/categories/...`` listing URLs return an empty response body when
  fetched server-side; the mega listing at ``/shop-coffee`` renders every
  product section statically, so it is used as the single store URL.
- Product URLs are ``/products/<opaque-hash>/<numeric-id>`` — the slug carries
  no words, so coffee filtering must use the product name from the listing
  card, not the URL.
- Prices are in KES (Kenyan shillings) in the static HTML. Zoho has a
  client-side multi-currency switcher, so the currency is pinned to KES in
  ``postprocess_extracted_bean`` as a guard against geo-conversion.
- Sold-out state is NOT rendered on the /shop-coffee listing (no
  out-of-stock classes or attributes on product cards); it is only available
  on the product detail page (``data-zs-out-of-stock`` variant attributes and
  "Out of stock" text). Stock status is therefore determined per product page
  by the AI extractor (in_stock=false when "out of stock" appears) rather
  than by listing-level filtering.
"""

import logging
import re

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="roast-republik",
    display_name="Roast Republik",
    roaster_name="Roast Republik",
    website="https://www.kenyan-coffee.com",
    description="Kenyan specialty coffee roaster (Roast and Grind Africa Ltd) based in Nakuru, "
    "roasting single-origin Kenyan beans and house blends under the Roast Republik brand, "
    "alongside a coffee roasting academy and green coffee sourcing",
    requires_api_key=True,
    currency="KES",
    country="Kenya",
    status="available",
)
class RoastRepublikScraper(BaseScraper):
    """Scraper for Roast Republik (www.kenyan-coffee.com, Zoho Commerce) with AI extraction."""

    def __init__(self, api_key: str | None = None):
        """Initialize Roast Republik scraper.

        Args:
            api_key: Google API key for Gemini. If None, will try environment variable.
        """
        super().__init__(
            roaster_name="Roast Republik",
            base_url="https://www.kenyan-coffee.com",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Zoho's /categories/* pages return an empty body to server-side
        fetches, so the static /shop-coffee mega listing (which contains all
        product sections) is used instead.

        Returns:
            List containing the store URL
        """
        return ["https://www.kenyan-coffee.com/shop-coffee"]

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
            use_playwright=False,  # Product pages render fully server-side
            use_optimized_mode=False,
        )

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract coffee bean product URLs from the /shop-coffee listing.

        # Sold-out detection: not available on the Zoho listing (cards carry
        # no stock markers); stock status is resolved per product page by the
        # AI extractor from the page's "Out of stock" text / data-zs attributes.

        Args:
            store_url: URL of the store page

        Returns:
            List of product URLs for coffee beans/blends
        """
        soup = await self.fetch_page(store_url)
        if not soup:
            return []

        # Zoho Commerce listing cards: the product name link lives in
        # div.theme-product-name with the product title in the title attribute.
        seen: set[str] = set()
        bean_urls: list[str] = []
        excluded_count = 0

        for link in soup.select("div.theme-product-name a[href^='/products/']"):
            url = self.resolve_url(link.get("href", ""))
            if not url or url in seen:
                continue

            name = (link.get("title") or link.get_text(" ", strip=True) or "").strip()
            if not self._is_bean_product_name(name):
                excluded_count += 1
                logger.debug(f"Excluding non-bean product: {name!r} ({url})")
                continue

            seen.add(url)
            bean_urls.append(url)
            logger.debug(f"Including coffee bean product: {name!r} ({url})")

        logger.info(
            f"Found {len(bean_urls)} coffee bean URLs out of {len(bean_urls) + excluded_count} products on {store_url}"
        )
        return bean_urls

    def _is_bean_product_name(self, name: str) -> bool:
        """Check whether a listing product name is a retail coffee bean/blend product.

        Product URLs on this site are opaque (/products/<hash>/<id>), so
        filtering must run on the product name. Wholesale (café supply) bags,
        roasting courses, mobile-bar experiences and brewing equipment are
        excluded. Tasting kits/samplers are NOT excluded — they must flow
        through with is_tasting_kit/requires_review flags per project policy.

        Args:
            name: Product name from the listing card

        Returns:
            True if the product is a coffee bean/blend product
        """
        name_lower = name.lower()

        # Non-coffee sections: courses, experiences, equipment
        excluded_terms = [
            "wholesale",  # B2B café-supply bags (own listing section)
            "certificate",  # Roasting academy courses
            "course",  # Roasting academy courses
            "training",
            "bar experience",  # Mobile bar services
            "grinder",
            "knock box",
            "tamper",
            "pitcher",
            "milk jug",
            "server",
            "chemex",
            "v60",
            "kettle",
            "mug",
            "gift card",
            "subscription",
        ]
        if any(term in name_lower for term in excluded_terms):
            return False

        # Retail beans: "HUSTLE KENYA AB COFFEE BEANS", "PLUG KENYAN COFFEE
        # BLEND", "MOTO COFFEE - KENYA HOME USE BEANS", etc.
        return bool(re.search(r"\bbeans?\b|\bblend\b", name_lower))

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Pin the currency to KES.

        Zoho Commerce has a client-side multi-currency switcher that can
        render geo-converted prices, so the registry currency (KES) is
        enforced on every extracted bean.

        Args:
            bean: Extracted CoffeeBean object

        Returns:
            Postprocessed CoffeeBean object
        """
        bean.currency = "KES"
        return bean
