"""Connect Coffee Roasters scraper implementation.

Connect Coffee Roasters (https://connectcoffeeroasters.net) is a specialty
coffee roaster and café based in Nairobi, Kenya. Their storefront runs on the
Hostinger Website Builder (Zyro), which is neither Shopify nor Squarespace:

- There is no products.json endpoint; the sitemap.xml lists every page,
  including one root-level URL per product (``/<slug>``).
- The /shop listing page renders its product grid client-side, but every
  product detail page is server-rendered with an h1, subtitle, price, a short
  description and a schema.org JSON-LD ``Product`` block carrying
  ``offers.price`` / ``offers.priceCurrency`` (always ``kes``) and
  ``offers.availability``.

The catalogue is heavily skewed toward barista equipment (espresso machines,
grinders, kettles, filter papers, ...) — roughly 85 of ~88 product pages.
Actual coffee is limited to the Romeo/Juliet roasted-bean blends and the
Barista Pouch drip pouches, all of which carry recognizable slug keywords, so
discovery uses a coffee-keyword include filter on the slug instead of the
base class' exclusion-only approach.
"""

import json
import logging
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag

from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)

# Non-product pages listed in sitemap.xml.
STATIC_PAGES = {"", "/shop", "/menu", "/contact", "/our-story", "/services"}

# Coffee products on this store are consistently named around these slug
# fragments ("Roasted Coffee Beans ... Blend", "Roasted Beans ... 250g",
# "Barista Pouch"). Everything else in the catalogue is barista equipment
# whose slugs frequently contain the word "coffee" (e.g. hario-coffee-grinder,
# acuba-coffee-scale), so a keyword *include* filter is far more reliable here
# than an exclusion list.
COFFEE_SLUG_KEYWORDS = [
    "coffee-bean",
    "beans",
    "coffee-blend",
    "barista-pouch",
    "single-origin",
]


@register_scraper(
    name="connect-coffee-roasters",
    display_name="Connect Coffee Roasters",
    roaster_name="Connect Coffee Roasters",
    website="https://connectcoffeeroasters.net",
    description="Nairobi-based specialty coffee roaster and café selling Romeo and Juliet "
    "roasted-bean blends (250g/1kg) plus Barista Pouch drip pouches, alongside "
    "barista equipment and café services",
    requires_api_key=True,
    currency="KES",
    country="Kenya",
    status="available",
)
class ConnectCoffeeRoastersScraper(BaseScraper):
    """Scraper for Connect Coffee Roasters (connectcoffeeroasters.net).

    The site is a Hostinger Website Builder storefront: product URLs live at
    the domain root, product pages are server-rendered, and sitemap.xml is
    the only complete product index.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize the scraper.

        Args:
            api_key: Optional API key for AI-powered extraction.
        """
        super().__init__(
            roaster_name="Connect Coffee Roasters",
            base_url="https://connectcoffeeroasters.net",
            rate_limit_delay=1.0,
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = None
        try:
            from ..ai import CoffeeDataExtractor

            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
        except ImportError:
            logger.warning("AI extractor not available - falling back to traditional extraction")

        # Ready-to-drink cold brew bottles are beverages, not beans (matching
        # the "cold-brew-cans" convention used by the Shopify scrapers).
        self.exclude_slugs = ["cold-brew"]

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        The Hostinger builder exposes no collection index; sitemap.xml is the
        complete, authoritative list of product pages.

        Returns:
            List containing the sitemap URL
        """
        return [f"{self.base_url}/sitemap.xml"]

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract coffee product URLs from the sitemap.

        Sold-out detection: the /shop listing grid is rendered client-side, so
        availability cannot be read from the listing. Instead each candidate
        product page's schema.org JSON-LD ``Product/offers.availability`` is
        checked (InStock is kept, OutOfStock is skipped) before the coffee
        URL filtering.

        Args:
            store_url: The sitemap URL

        Returns:
            List of in-stock coffee product URLs
        """
        response = await self.client.get(store_url)
        response.raise_for_status()
        # sitemap.xml is genuine XML; parse it with the XML parser to avoid
        # XMLParsedAsHTMLWarning noise from the HTML parser.
        soup = BeautifulSoup(response.text, "xml")

        candidates: list[str] = []
        for loc in soup.find_all("loc"):
            url = loc.get_text(strip=True)
            if not url:
                continue

            path = urlparse(url).path.rstrip("/")
            if path in STATIC_PAGES:
                continue

            slug = path.lstrip("/")
            if not slug:
                continue

            # Skip ready-to-drink cold brew and any other excluded slugs.
            if any(excluded in slug for excluded in self.exclude_slugs):
                logger.debug(f"Skipping excluded product slug: {slug}")
                continue

            # Coffee-keyword include filter (see COFFEE_SLUG_KEYWORDS note).
            if not any(keyword in slug for keyword in COFFEE_SLUG_KEYWORDS):
                logger.debug(f"Skipping non-coffee product slug: {slug}")
                continue

            candidates.append(url)

        candidates = self.deduplicate_urls(candidates)

        # Sold-out detection via per-product JSON-LD availability.
        in_stock_urls: list[str] = []
        for url in candidates:
            if await self._is_in_stock(url):
                in_stock_urls.append(url)
            else:
                logger.info(f"Skipping sold-out product: {url}")

        logger.info(f"Found {len(in_stock_urls)} in-stock coffee products from {store_url}")
        return in_stock_urls

    async def _is_in_stock(self, product_url: str) -> bool:
        """Check a product page's JSON-LD offers.availability.

        Args:
            product_url: Product page URL

        Returns:
            True if the JSON-LD marks the product InStock (or availability
            cannot be determined, to stay conservative)
        """
        try:
            response = await self.client.get(product_url)
            response.raise_for_status()
        except Exception as e:
            logger.warning(f"Failed to fetch {product_url} for stock check ({e}); including it")
            return True

        soup = BeautifulSoup(response.text, "lxml")
        ld_json = soup.find("script", type="application/ld+json")
        if not isinstance(ld_json, Tag):
            return True

        try:
            data = json.loads(ld_json.string or "{}")
        except (json.JSONDecodeError, TypeError):
            return True

        availability = ""
        offers = data.get("offers")
        if isinstance(offers, dict):
            availability = str(offers.get("availability", ""))
        elif isinstance(offers, list) and offers:
            availability = str(offers[0].get("availability", ""))

        return "outofstock" not in availability.lower()

    async def fetch_page(self, *args, **kwargs) -> BeautifulSoup | Tag | None:
        """Fetch a page, narrowing product pages to the product block.

        Hostinger builder pages ship ~170KB of serialized builder payload per
        product page. The visible product content (title, subtitle, price,
        description, image) all live inside a single ``div.block-product-wrapper``,
        so product pages are narrowed to that container before AI extraction.
        Non-product pages (sitemap, static pages) are returned untouched.

        Args:
            *args: Positional arguments (url first)
            **kwargs: Keyword arguments (url, use_playwright, ...)

        Returns:
            Narrowed BeautifulSoup object, or None if fetch failed
        """
        try:
            soup = await super().fetch_page(*args, **kwargs)

            url = kwargs.get("url")
            if not url and len(args) > 0:
                url = args[0]

            path = urlparse(url or "").path.rstrip("/")
            if path in STATIC_PAGES or path.endswith(".xml"):
                return soup

            product_el = soup.select("div.block-product-wrapper") if soup else []
            if len(product_el) == 1:
                return product_el[0]

            logger.warning(f"No product block found for URL {url}; returning full page")
            return soup
        except Exception as e:
            logger.error(f"Error fetching page: {e}")
            return None

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Pin the currency to KES.

        The storefront serves prices in Kenyan Shilling only (confirmed from
        the JSON-LD ``priceCurrency: "kes"``), but force it as a final guard
        against AI-extraction drift.

        Args:
            bean: Extracted CoffeeBean object

        Returns:
            Postprocessed CoffeeBean object
        """
        bean.currency = "KES"
        return bean

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products using full AI extraction.

        Args:
            product_urls: List of URLs for new products

        Returns:
            List of newly scraped CoffeeBean objects
        """

        async def get_new_product_urls(store_url: str) -> list[str]:
            return product_urls

        return await self.scrape_with_ai_extraction(
            extract_product_urls_function=get_new_product_urls,
            ai_extractor=self.ai_extractor,
            use_playwright=False,  # Product pages are fully server-rendered
            use_optimized_mode=False,  # Narrowed product block is fed to the AI
            translate_to_english=False,  # Site is in English
        )
