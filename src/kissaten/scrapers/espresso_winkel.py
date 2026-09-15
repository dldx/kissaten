"""Espresso Winkel scraper implementation with AI extraction.

Espresso Winkel (espressowinkel.nl) is a Dutch coffee gear shop built on the
Lightspeed eCom platform (webshopapp.com CDN) with its own roastery. Its
roasted-coffee catalogue is split across two collection pages:

- ``/koffie/gebrande-koffie/`` (roasted coffee, incl. single origins, blends
  and "proefpakketten" tasting kits)
- ``/koffie/the-fermentation-project-van-james-hoffmann/`` (the James Hoffmann
  "The Fermentation Project" kits)

Discovery notes (2026-09, curl-first):
- Platform: Lightspeed eCom. ``products.json`` 404s (not Shopify).
- Lightspeed exposes a clean AJAX listing JSON per collection at
  ``<collection-path>/pageN.ajax?format=json`` returning ``{"count": ..,
  "pages": .., "products": [{"url", "title", "available", "price", ..}]}``.
  This doubles as the sold-out detector (``available == false``) and removes
  the need to parse the (static-markup-polluted) HTML listing: the hover
  quick-buy popup embeds an ``unavailable-product-popup`` span in *every*
  card regardless of stock, so HTML text detection is unreliable here.
- Product URLs are flat ``<slug>.html`` at the domain root.
"""

import logging
from pathlib import Path

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)

STORE_URLS = [
    "https://www.espressowinkel.nl/koffie/gebrande-koffie/",
    "https://www.espressowinkel.nl/koffie/the-fermentation-project-van-james-hoffmann/",
]

# Dutch non-coffee items sold inside the roasted-coffee category
# (cadeaubon = gift card). Everything else in the category is coffee.
EXCLUDED_URL_PATTERNS = [
    "cadeaubon",
]


def _is_fermentation_project_kit(url: str) -> bool:
    """Return True if the URL is one of the James Hoffmann Fermentation Project kits."""
    return "the-fermentation-project" in url.lower()


@register_scraper(
    name="espresso-winkel",
    display_name="Espresso Winkel",
    roaster_name="Espresso Winkel",
    website="https://www.espressowinkel.nl",
    description=(
        "Dutch coffee equipment specialist and roastery in Venlo, offering "
        "its own roasted beans plus the James Hoffmann 'The Fermentation "
        "Project' tasting kits."
    ),
    requires_api_key=True,
    currency="EUR",
    country="Netherlands",
    status="experimental",
)
class EspressoWinkelScraper(BaseScraper):
    """Scraper for Espresso Winkel (espressowinkel.nl) — a Lightspeed eCom storefront.

    Model: ``koppi.py`` (AI extraction of product pages) combined with the
    Lightspeed per-collection AJAX JSON listing endpoint for URL discovery and
    sold-out detection.
    """

    def __init__(self, api_key: str | None = None):
        """Initialize Espresso Winkel scraper."""
        super().__init__(
            roaster_name="Espresso Winkel",
            base_url="https://www.espressowinkel.nl",
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = CoffeeDataExtractor(api_key=api_key)

    async def get_store_urls(self) -> list[str]:
        """Return the two roasted-coffee collection URLs."""
        return list(STORE_URLS)

    async def _fetch_lightspeed_products(self, store_url: str) -> list[dict]:
        """Fetch all products of a Lightspeed collection via its AJAX JSON listing.

        Walks ``<collection>/pageN.ajax?format=json`` from page 1 until the
        reported page count is exhausted.

        Args:
            store_url: Collection page URL

        Returns:
            List of Lightspeed product dicts (url, title, available, price, ...)

        Raises:
            Exception: On HTTP or JSON errors (caller treats the listing as failed)
        """
        base = store_url.rstrip("/") + "/"
        products: list[dict] = []
        page = 1
        while True:
            ajax_url = f"{base}page{page}.ajax?format=json"
            response = await self.client.get(ajax_url)
            response.raise_for_status()
            data = response.json()
            page_products = data.get("products") or []
            products.extend(page_products)
            pages = int(data.get("pages") or 1)
            if not page_products or page >= pages:
                break
            page += 1
        return products

    def _keep_sold_out_fermentation_kit(self, url: str) -> bool:
        """Keep the Fermentation Project kits in the URL list even while sold out.

        The Hoffmann tasting kits must be extracted so they enter the
        tasting-kit review flow downstream. Once a kit has been scraped
        historically it is dropped from the current URL list again, so the
        next refresh correctly marks it out of stock via diffjson.
        """
        if not _is_fermentation_project_kit(url):
            return False
        self._load_existing_beans_from_all_sessions(Path("data"))
        return not self._is_bean_already_scraped_historically(url)

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract coffee product URLs from a Lightspeed collection.

        Args:
            store_url: Collection page URL

        Returns:
            List of in-stock coffee product URLs
        """
        # Sold-out detection: Lightspeed AJAX listing JSON "available" field
        # (available == false => sold out; verified against "Uganda 500 gram"
        # which is marked "Niet op voorraad" on the site but is InStock at the
        # product page — the AJAX flag is the authoritative one).
        try:
            products = await self._fetch_lightspeed_products(store_url)
        except Exception as e:
            logger.error(f"Failed to fetch Lightspeed listing JSON for {store_url}: {e}")
            return []

        urls = []
        for product in products:
            url = (product.get("url") or "").strip()
            if not url:
                continue
            if not product.get("available", True) and not self._keep_sold_out_fermentation_kit(url):
                logger.debug(f"Skipping sold-out product: {product.get('title')}")
                continue
            urls.append(url)

        # De-duplicate while preserving order
        urls = list(dict.fromkeys(urls))

        coffee_urls = [
            url
            for url in urls
            if self.is_coffee_product_url(url, required_path_patterns=[".html"])
            and not any(ex in url.lower() for ex in EXCLUDED_URL_PATTERNS)
        ]
        logger.info(
            f"Found {len(coffee_urls)} coffee product URLs out of {len(urls)} in-stock products from {store_url}"
        )
        return coffee_urls

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
            use_optimized_mode=False,
            translate_to_english=True,  # Dutch site — translate to English
        )

    def _get_excluded_url_patterns(self) -> list[str]:
        """Allow the Fermentation Project cupping-set product through.

        The base "cupping" exclusion targets cupping *sessions* (services);
        this roaster sells a physical Fermentation Project cupping-set kit
        which must be extracted and flagged as a tasting kit downstream.
        """
        return [p for p in super()._get_excluded_url_patterns() if p != "cupping"]

    def _get_tasting_kit_url_patterns(self) -> list[str]:
        """Add the Dutch tasting-kit slugs used by this roaster."""
        return super()._get_tasting_kit_url_patterns() + [
            "proefpakket",  # Dutch for tasting pack
            "the-fermentation-project",
        ]

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Pin EUR as the store currency (guards against the GBP fallback)."""
        bean.currency = "EUR"
        return bean
