"""NiR Coffee scraper implementation with structured JSON extraction.

NiR Coffee (nircoffee.id) is a specialty roaster in Indonesia. The public site
is a React SPA (``/shop`` and ``/shop/daily/...`` routes ship an empty 9.7 KB
shell), but the SPA's own backend exposes a complete public catalogue API:

    GET https://api.nircoffee.id/api/v1/public/products

Each product document already carries everything the bean schema needs —
single-origin country/region/producer/farm/varietals/process/altitude, roast
level and profile, tasting notes, story, per-variant weights plus prices in
IDR, availability and images. This scraper therefore consumes the JSON API
directly instead of running AI extraction over an empty SPA shell: it is
deterministic, key-free and complete.

Platform notes from curl-first discovery (2026-09):
- Every SPA route returns the same 9.7 KB shell (no static product markup), so
  HTML discovery is impossible without Playwright; the JSON API replaces it.
- Product URLs follow ``/shop/{daily|limited}/{espresso|filter}/<slugified name>``
  (verified against the hydrated ``/shop`` listing).
- The Fermentation Project × James Hoffmann kit (``productType: OTHER``,
  ``code: FERMENTATION_KIT_2026``) has no public shop route; it lives at
  ``/fermentation-project``.
"""

import csv
import json
import logging
import re
from functools import lru_cache
from pathlib import Path

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean, PriceOption
from ..schemas.coffee_bean import Bean, RoastLevel
from .base import BEAN_DATA_DIR, BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)

PRODUCTS_API_URL = "https://api.nircoffee.id/api/v1/public/products"
SITE_BASE_URL = "https://nircoffee.id"
_COUNTRY_CODES_PATH = Path(__file__).parent.parent / "database" / "countrycodes.csv"

# API roast level -> schema RoastLevel.
_ROAST_LEVELS = {
    "VERY_LIGHT": RoastLevel.EXTRA_LIGHT,
    "EXTRA_LIGHT": RoastLevel.EXTRA_LIGHT,
    "LIGHT": RoastLevel.LIGHT,
    "LIGHT_MEDIUM": RoastLevel.MEDIUM_LIGHT,
    "MEDIUM_LIGHT": RoastLevel.MEDIUM_LIGHT,
    "MEDIUM": RoastLevel.MEDIUM,
    "MEDIUM_DARK": RoastLevel.MEDIUM_DARK,
    "DARK": RoastLevel.DARK,
}

# API roast profile -> schema roast_profile literal.
_ROAST_PROFILES = {
    "ESPRESSO": "Espresso",
    "FILTER": "Filter",
    "ALL": "Omni",
    "OMNI": "Omni",
}


def _slugify(value: str) -> str:
    """Slugify a product name into the SPA's URL slug form.

    Args:
        value: Product name (e.g. "Flores Gulang #349 Natural Anaerob Fast Dry Filter").

    Returns:
        Lowercase hyphenated slug (e.g. "flores-gulang-349-natural-anaerob-fast-dry-filter").
    """
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").lower())
    return slug.strip("-")


@lru_cache(maxsize=1)
def _country_name_to_alpha2() -> dict[str, str]:
    """Load the country name -> ISO 3166-1 alpha-2 lookup used by the pipeline."""
    mapping: dict[str, str] = {}
    try:
        with open(_COUNTRY_CODES_PATH, newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                name = (row.get("name") or "").strip().lower()
                alpha2 = (row.get("alpha-2") or "").strip().upper()
                if name and alpha2:
                    mapping[name] = alpha2
    except OSError as e:
        logger.warning(f"Could not load country codes from {_COUNTRY_CODES_PATH}: {e}")
    return mapping


def _country_code(name: str | None) -> str | None:
    """Convert an API country name into the two-letter code the schema expects."""
    if not name:
        return None
    cleaned = name.strip()
    if len(cleaned) == 2:
        return cleaned.upper()
    return _country_name_to_alpha2().get(cleaned.lower(), cleaned)


def _parse_altitude(altitude: str | None) -> tuple[int, int]:
    """Parse an altitude string such as "1500-1700" or "1600" into (min, max) metres."""
    if not altitude:
        return 0, 0
    numbers = [int(match) for match in re.findall(r"\d+", str(altitude))]
    if not numbers:
        return 0, 0
    low, high = min(numbers), max(numbers)
    # Schema bounds are 0-3000 m.
    return min(low, 3000), min(high, 3000)


@register_scraper(
    name="nir-coffee",
    display_name="NiR Coffee",
    roaster_name="NiR Coffee",
    website="https://nircoffee.id",
    description="Specialty coffee roaster in Indonesia; catalogue is read from the store's public JSON API.",
    requires_api_key=True,
    currency="IDR",
    country="Indonesia",
    status="experimental",
)
class NirCoffeeScraper(BaseScraper):
    """Scraper for NiR Coffee (nircoffee.id) using the public store JSON API."""

    def __init__(self, api_key: str | None = None):
        """Initialize the NiR Coffee scraper.

        Args:
            api_key: Google API key for Gemini. The structured API supplies every
                field directly, but the key is accepted for interface parity.
        """
        super().__init__(
            roaster_name="NiR Coffee",
            base_url=SITE_BASE_URL,
            rate_limit_delay=2.0,
            max_retries=3,
            timeout=30.0,
        )

        self.ai_extractor = None
        try:
            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
        except ValueError:
            logger.warning("Google API key not configured. AI extraction will not be available.")

        # Products keyed by their public URL, populated during discovery.
        self._products_by_url: dict[str, dict] = {}

    async def get_store_urls(self) -> list[str]:
        """Get the public catalogue API URL.

        Returns:
            List containing the products API endpoint.
        """
        return [PRODUCTS_API_URL]

    async def _fetch_products(self) -> list[dict] | None:
        """Fetch the full public product catalogue.

        Returns:
            List of product documents, or None when the API call failed.
        """
        try:
            response = await self.client.get(PRODUCTS_API_URL)
        except Exception as e:
            logger.warning(f"Failed to fetch {PRODUCTS_API_URL}: {e}")
            return None

        if response.status_code != 200:
            logger.warning(f"NiR products API returned HTTP {response.status_code}")
            return None

        try:
            payload = response.json()
        except (ValueError, json.JSONDecodeError) as e:
            logger.warning(f"NiR products API did not return JSON: {e}")
            return None

        products = payload.get("data")
        if not isinstance(products, list):
            logger.warning("Unexpected NiR products API payload shape")
            return None
        return products

    def _product_url(self, product: dict) -> str | None:
        """Build the public shop URL for a product.

        Args:
            product: API product document.

        Returns:
            Public URL, or None for products without a shop route.
        """
        name = product.get("name") or ""
        if product.get("productType") == "OTHER" or "fermentation" in name.lower():
            return f"{SITE_BASE_URL}/fermentation-project"

        slug = _slugify(name)
        if not slug:
            return None

        profile_config = product.get("roastProfileConfig") or {}
        green_bean_profile = product.get("greenBeanProfile") or {}
        profile = (profile_config.get("roastProfile") or green_bean_profile.get("supportedRoastProfile") or "").upper()
        profile_segment = "filter" if profile == "FILTER" else "espresso"

        series = (green_bean_profile.get("type") or "DAILY").upper()
        series_segment = "limited" if series == "LIMITED" else "daily"

        return f"{SITE_BASE_URL}/shop/{series_segment}/{profile_segment}/{slug}"

    @staticmethod
    def _is_in_stock(product: dict) -> bool:
        """Return True when at least one variant is available for purchase."""
        for variant in product.get("variants") or []:
            if not variant.get("isAvailable"):
                continue
            quantity = variant.get("availableUnitQty")
            if quantity is None or float(quantity) > 0:
                return True
        return False

    # Sold-out detection: the API's per-variant `isAvailable` flag (+ the
    # availableUnitQty counter). Products with no purchasable variant are left
    # out of the current URL list so the base class records them as an
    # out-of-stock update instead of an in-stock refresh.
    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Extract in-stock coffee product URLs from the public catalogue API.

        Args:
            store_url: The products API URL.

        Returns:
            List of in-stock product URLs.
        """
        products = await self._fetch_products()
        if products is None:
            # Do not let a failed catalogue fetch wipe the known catalogue.
            return []

        product_urls: list[str] = []
        seen: set[str] = set()

        for product in products:
            if product.get("isArchived") or product.get("isReleased") is False:
                logger.debug(f"Skipping archived/unreleased product: {product.get('name')}")
                continue

            if not self._is_in_stock(product):
                logger.debug(f"Skipping sold-out product: {product.get('name')}")
                continue

            url = self._product_url(product)
            if not url:
                continue

            self._products_by_url[url] = product

            if url not in seen:
                seen.add(url)
                product_urls.append(url)

        logger.info(f"Found {len(product_urls)} in-stock coffee product URLs from {store_url}")
        return product_urls

    def _build_bean(self, product: dict, url: str) -> CoffeeBean | None:
        """Build a validated CoffeeBean directly from an API product document.

        Args:
            product: API product document.
            url: Public product URL.

        Returns:
            CoffeeBean, or None when the product has no usable data.
        """
        name = (product.get("name") or "").strip()
        if not name:
            return None

        price_options: list[PriceOption] = []
        for variant in product.get("variants") or []:
            pricing = variant.get("pricing") or []
            retail = next(
                (entry for entry in pricing if (entry.get("pricingTypeCode") or "").upper() == "RETAIL"),
                pricing[0] if pricing else None,
            )
            if not retail:
                continue
            try:
                price = float(retail.get("price"))
            except (TypeError, ValueError):
                continue
            if price <= 0:
                continue

            weight = None
            try:
                grams = int(round(float(variant.get("weightGrams"))))
                if 10 < grams <= 10000:
                    weight = grams
            except (TypeError, ValueError):
                weight = None

            price_options.append(PriceOption(weight=weight, price=price, currency="IDR"))

        if not price_options:
            logger.warning(f"No usable prices for {name} ({url})")
            return None

        origins: list[Bean] = []
        green_bean_profile = product.get("greenBeanProfile") or {}
        if product.get("productType") != "OTHER":
            elevation_min, elevation_max = _parse_altitude(green_bean_profile.get("altitude"))
            origins.append(
                Bean(
                    country=_country_code(green_bean_profile.get("country")),
                    region=(green_bean_profile.get("region") or "").strip() or None,
                    producer=(green_bean_profile.get("producer") or "").strip() or None,
                    farm=(green_bean_profile.get("farm") or "").strip() or None,
                    variety=(green_bean_profile.get("varietals") or "").strip() or None,
                    process=(green_bean_profile.get("process") or "").strip() or None,
                    elevation_min=elevation_min,
                    elevation_max=elevation_max,
                )
            )

        tasting_notes = [
            note.strip() for note in re.split(r"[,;\n]", product.get("tastingNotes") or "") if note.strip()
        ]

        image_url = None
        images = product.get("images") or []
        if images:
            primary = next((image for image in images if image.get("isPrimary")), images[0])
            image_url = primary.get("url")

        cheapest = min(price_options, key=lambda option: option.price)

        roast_level = _ROAST_LEVELS.get((product.get("roastLevel") or "").upper())
        profile_config = product.get("roastProfileConfig") or {}
        roast_profile = _ROAST_PROFILES.get((profile_config.get("roastProfile") or "").upper())

        return CoffeeBean(
            name=name[:200],
            roaster=self.roaster_name,
            url=url,
            image_url=image_url,
            description=(product.get("story") or "").strip() or None,
            origins=origins,
            is_single_origin=product.get("productType") == "COFFEE_SINGLE_ORIGIN",
            roast_level=roast_level,
            roast_profile=roast_profile,
            price_options=price_options,
            price=cheapest.price,
            weight=cheapest.weight,
            currency="IDR",
            is_decaf=False,
            tasting_notes=tasting_notes,
            in_stock=True,
            scraper_version="2.0",
        )

    async def _scrape_new_products(self, product_urls: list[str]) -> list[CoffeeBean]:
        """Scrape new products by building beans from the catalogue API documents.

        Args:
            product_urls: List of URLs for new products.

        Returns:
            List of newly scraped CoffeeBean objects.
        """
        if not product_urls:
            return []

        # Refresh the cached catalogue if discovery ran in a previous session.
        if not self._products_by_url:
            await self._extract_product_urls_from_store(PRODUCTS_API_URL)

        beans: list[CoffeeBean] = []
        for url in product_urls:
            product = self._products_by_url.get(url)
            if not product:
                logger.warning(f"No cached API document for {url}")
                continue

            try:
                bean = self._build_bean(product, url)
            except Exception as e:
                logger.error(f"Failed to build bean for {url}: {e}")
                continue
            if not bean:
                continue

            self._apply_product_flags(bean, url, is_new=True)
            bean = self.postprocess_extracted_bean(bean)
            if not bean:
                continue

            await self.save_bean_with_image(bean, BEAN_DATA_DIR)
            self._mark_bean_as_scraped(url)
            beans.append(bean)

        return beans

    def postprocess_review_flags(self, bean: CoffeeBean, url: str) -> CoffeeBean:
        """Flag the Fermentation Project tasting kit for admin review."""
        haystack = f"{url} {getattr(bean, 'name', '') or ''}".lower()
        if "fermentation" in haystack:
            bean.is_tasting_kit = True
        return bean

    def postprocess_extracted_bean(self, bean: CoffeeBean) -> CoffeeBean | None:
        """Pin the store currency (the registry lookup by display name can fall back to GBP)."""
        bean.currency = "IDR"
        return bean
