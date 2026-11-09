"""DAK Coffee Roasters scraper using the WooCommerce Store API.

DAK Coffee migrated its shop from a custom API (``/api/products/all``, now
removed/404) to WordPress + WooCommerce. Products are fetched from the public
WooCommerce Store API (``/wp-json/wc/store/v1/products``), which returns
structured attributes (origin, region, process, varietal, tasting notes,
altitude, weights) so beans are parsed deterministically without AI extraction.
"""

import asyncio
import html
import json
import logging
import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from ..schemas import CoffeeBean, CoffeeBeanDiffUpdate, PriceOption
from ..schemas.coffee_bean import Bean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)

PRODUCTS_API_URL = "https://www.dakcoffeeroasters.com/wp-json/wc/store/v1/products"
_COUNTRY_CODES_PATH = Path(__file__).parent.parent / "database" / "countrycodes.csv"

# Product categories that contain coffee beans (vs. wear/goods merchandise).
_COFFEE_CATEGORY_SLUGS = {"espresso", "filter"}
# Slugs to exclude even if categorized as coffee (e.g. the "Steeped" bag-in-box packs).
_EXCLUDED_SLUGS = ["steeped"]


@lru_cache(maxsize=1)
def _country_name_to_alpha2() -> dict[str, str]:
    """Load a country-name -> alpha-2 code mapping from the bundled CSV."""
    import csv

    mapping: dict[str, str] = {}
    try:
        with open(_COUNTRY_CODES_PATH, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                mapping[row["name"].strip().lower()] = row["alpha-2"].strip()
    except FileNotFoundError:
        logger.warning(f"Country codes CSV not found at {_COUNTRY_CODES_PATH}")
    return mapping


def _minor_unit_price(amount: str | int | None, minor_unit: int | None) -> float | None:
    """Convert a WooCommerce minor-unit price string (e.g. "1780") to a float.

    Args:
        amount: Raw amount from the API (string or int, in minor units).
        minor_unit: Number of decimal digits (currency_minor_unit, e.g. 2 for EUR).

    Returns:
        Price in major currency units, or None if the amount is missing/invalid.
    """
    if amount in (None, ""):
        return None
    try:
        value = float(amount)
    except (TypeError, ValueError):
        return None
    return value / (10 ** (minor_unit if minor_unit is not None else 2))


def _parse_weight_grams(text: str) -> int | None:
    """Parse a weight label like "250g", "1kg" or "125 g" into grams."""
    if not text:
        return None
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(kg|g)\b", text.lower())
    if not m:
        return None
    value = float(m.group(1).replace(",", "."))
    if m.group(2) == "kg":
        value *= 1000
    return int(value)


def _parse_elevation(altitude: str) -> tuple[int, int]:
    """Parse an altitude label like "1260masl" or "1650-2000masl" into (min, max)."""
    numbers = [int(n) for n in re.findall(r"\d+", altitude or "")]
    if not numbers:
        return 0, 0
    return min(numbers), max(numbers)


@register_scraper(
    name="dak-coffee",
    display_name="DAK Coffee Roasters",
    roaster_name="DAK Coffee Roasters",
    website="https://www.dakcoffeeroasters.com",
    description="Dutch specialty coffee roasters, based in Amsterdam",
    requires_api_key=False,
    currency="EUR",
    country="Netherlands",
    status="available",
)
class DakCoffeeScraper(BaseScraper):
    """Scraper for DAK Coffee Roasters using their WooCommerce Store API."""

    def __init__(self, api_key: str | None = None):
        """Initialize DAK Coffee scraper.

        Args:
            api_key: Not used for this scraper since we use their API directly
        """
        super().__init__(
            roaster_name="DAK Coffee Roasters",
            base_url="https://www.dakcoffeeroasters.com",
            rate_limit_delay=1.0,
            max_retries=3,
            timeout=30.0,
        )

    async def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Note: This method is not used for API-based scraping but is required by the base class.

        Returns:
            Empty list since we use API endpoint directly
        """
        return []

    async def scrape(
        self, output_dir=None, force_full_update: bool = False, create_diffjson_updates: bool = True
    ) -> list[CoffeeBean]:
        """Scrape coffee beans from DAK Coffee Roasters using their WooCommerce Store API.

        Args:
            output_dir: Output directory for saving files (optional)
            force_full_update: If True, scrape all products regardless of whether they exist
            create_diffjson_updates: If True, create diffjson updates for existing products

        Returns:
            List of CoffeeBean objects
        """
        session = self.start_session()
        coffee_beans = []

        try:
            # Set up output directory
            if output_dir is None:
                output_dir = Path("data")
            else:
                output_dir = Path(output_dir)

            self._load_existing_beans_for_session(output_dir)

            # Call the Store API (paginated)
            logger.info(f"Fetching data from DAK Coffee Store API: {PRODUCTS_API_URL}")
            products = await self._fetch_all_products()
            session.requests_made += 1

            coffee_products = self._filter_coffee_products(products)
            logger.info(f"Found {len(products)} products ({len(coffee_products)} coffee) from DAK Coffee Store API")

            # Extract all current product URLs for diffjson processing
            current_product_urls = [self._product_url(p) for p in coffee_products]

            # Create diffjson stock updates for existing products if enabled
            in_stock_count = 0
            out_of_stock_count = 0
            if create_diffjson_updates:
                in_stock_count, out_of_stock_count = await self._create_api_based_diffjson_updates(
                    coffee_products, current_product_urls, output_dir, force_full_update
                )

            # Process each product
            for product in coffee_products:
                try:
                    product_url = self._product_url(product)

                    # Skip if already scraped in this session
                    if self._is_bean_already_scraped_in_session(product_url):
                        logger.debug(f"Skipping already scraped product: {product.get('name')}")
                        continue

                    # If not forcing full update and diffjson is enabled, skip existing products
                    # (they've already been handled by diffjson updates)
                    if not force_full_update and create_diffjson_updates:
                        if self._is_bean_already_scraped_historically(product_url):
                            logger.debug(f"Skipping existing product (handled by diffjson): {product.get('name')}")
                            continue

                    coffee_bean = self._parse_product(product)

                    if coffee_bean:
                        self._apply_product_flags(coffee_bean, product_url)
                        coffee_beans.append(coffee_bean)
                        self._mark_bean_as_scraped(product_url)

                except Exception as e:
                    logger.warning(f"Error processing product {product.get('name')}: {e}")
                    session.add_error(f"Error processing product: {e}")
                    continue

            # Log summary
            total_products = len(coffee_products)
            skipped_count = total_products - len(coffee_beans)
            if skipped_count > 0:
                logger.info(f"Skipped {skipped_count} already scraped products from today's session")
            logger.info(f"Successfully processed {len(coffee_beans)} new coffee beans")

            # Log diffjson summary if enabled
            if create_diffjson_updates:
                logger.info(f"Created diffjson updates: {in_stock_count} in-stock, {out_of_stock_count} out-of-stock")

            # Save beans to individual JSON files
            if coffee_beans:
                saved_files = []
                for bean in coffee_beans:
                    saved_files.append(await self.save_bean_with_image(bean, output_dir))
                logger.info(f"Saved {len(saved_files)} coffee bean files to {output_dir}")

            # Update session stats
            session.beans_found = total_products
            session.beans_processed = len(coffee_beans)
            session.beans_found_in_stock = total_products

            self.end_session(success=True)
            return coffee_beans

        except Exception as e:
            logger.error(f"Error fetching data from DAK Coffee Store API: {e}")
            session.add_error(f"API error: {e}")
            # The listing fetch failed this session — "not found" is untrustworthy,
            # so out-of-stock updates must be suppressed (see BaseScraper guard).
            self._failed_listing_urls.append(PRODUCTS_API_URL)
            self.end_session(success=False)
            return []

    async def _fetch_all_products(self) -> list[dict]:
        """Fetch all products from the WooCommerce Store API, following pagination.

        Returns:
            List of raw product dicts.

        Raises:
            httpx.HTTPError: On any request failure (propagated to scrape()).
        """
        products: list[dict] = []
        page = 1
        while True:
            response = await self.client.get(PRODUCTS_API_URL, params={"per_page": 100, "page": page})
            response.raise_for_status()
            page_products = response.json()
            products.extend(page_products)
            total_pages = int(response.headers.get("x-wp-totalpages", "1") or "1")
            if page >= total_pages:
                break
            page += 1
            await asyncio.sleep(self.rate_limit_delay)
        return products

    def _filter_coffee_products(self, products: list[dict]) -> list[dict]:
        """Keep only products in coffee categories, excluding known non-bean slugs."""
        coffee = []
        for product in products:
            category_slugs = {c.get("slug") for c in product.get("categories", [])}
            if not category_slugs & _COFFEE_CATEGORY_SLUGS:
                continue
            slug = product.get("slug", "")
            if any(excluded in slug for excluded in _EXCLUDED_SLUGS):
                logger.debug(f"Skipping excluded product slug: {slug}")
                continue
            coffee.append(product)
        return coffee

    def _product_url(self, product: dict) -> str:
        """Build the canonical product URL from the Store API permalink."""
        return (product.get("permalink") or "").rstrip("/")

    def _get_attributes(self, product: dict) -> dict[str, list[str]]:
        """Flatten product attributes into a name -> [term names] mapping."""
        attrs: dict[str, list[str]] = {}
        for attr in product.get("attributes", []):
            name = (attr.get("name") or "").strip()
            terms = [t.get("name", "").strip() for t in attr.get("terms", []) if t.get("name")]
            if name and terms:
                attrs[name] = terms
        return attrs

    def _parse_product(self, product: dict) -> CoffeeBean | None:
        """Parse a Store API product into a CoffeeBean deterministically.

        Args:
            product: Raw product dict from the WooCommerce Store API.

        Returns:
            CoffeeBean object or None if required fields are missing.
        """
        name = (product.get("name") or "").strip()
        product_url = self._product_url(product)
        if not name or not product_url:
            return None

        prices = product.get("prices", {})
        currency = (prices.get("currency_code") or "EUR").upper()
        minor_unit = prices.get("currency_minor_unit")
        price_range = prices.get("price_range") or {}
        price = _minor_unit_price(price_range.get("min_amount") or prices.get("price"), minor_unit)
        if price is None:
            logger.warning(f"Skipping product without a parseable price: {name}")
            return None

        attrs = self._get_attributes(product)

        # Weights (grams) from the "Weight" attribute; the lowest weight pairs with
        # the min price from the price range.
        weights = sorted(w for w in (_parse_weight_grams(t) for t in attrs.get("Weight", [])) if w)
        weight = weights[0] if weights else None

        # Build the origin(s)
        origin_names = attrs.get("Origin", [])
        origins = self._build_origins(attrs, origin_names)
        is_single_origin = len(origin_names) <= 1

        # Roast profile: both profiles offered as separate options -> "Both"
        roast_terms = attrs.get("Roast Profile", [])
        roast_profile = None
        if roast_terms:
            roast_profile = "Both" if len(roast_terms) > 1 else roast_terms[0].title()

        # Price options: the API exposes only the price range, so pair the
        # base (min) price with the smallest available weight.
        price_options = [PriceOption(weight=weight, price=price, currency=currency)]

        # Decaf flag from name/attributes
        haystack = (name + " " + " ".join(attrs.get("Process", []))).lower()
        is_decaf = "decaf" in haystack

        description = self._strip_html(product.get("description") or product.get("short_description") or "")

        images = product.get("images") or []
        image_url = images[0].get("src") if images and images[0].get("src") else None

        return CoffeeBean(
            name=name,
            roaster="DAK Coffee Roasters",
            url=product_url,
            image_url=image_url,
            description=description or None,
            origins=origins,
            is_single_origin=is_single_origin,
            roast_profile=roast_profile,
            price_options=price_options,
            price=price,
            weight=weight,
            currency=currency,
            is_decaf=is_decaf,
            tasting_notes=attrs.get("Tasting notes", []),
            in_stock=product.get("is_in_stock", True),
            scraper_version="3.0",
            raw_data=json.dumps(product, ensure_ascii=False),
        )

    def _build_origins(self, attrs: dict[str, list[str]], origin_names: list[str]) -> list[Bean]:
        """Build Bean origin entries from the structured attributes.

        Single-origin products get the full region/producer/elevation/process/
        varietal detail; blends get one minimal Bean per origin country.
        """
        countries = [self._to_country_code(o) for o in origin_names]
        countries = [c for c in countries if c]
        if not countries:
            return [Bean()]

        if len(countries) > 1:
            return [Bean(country=c) for c in countries]

        regions = attrs.get("Region", [])
        producers = [re.sub(r"^Produced by\s+", "", t, flags=re.IGNORECASE) for t in attrs.get("Producer / Farm", [])]
        altitudes = attrs.get("Altitude", [])
        elevation_min, elevation_max = _parse_elevation(altitudes[0]) if altitudes else (0, 0)
        processes = attrs.get("Process", [])
        varietals = attrs.get("Varietal", [])

        return [
            Bean(
                country=countries[0],
                region=regions[0] if regions else None,
                producer=producers[0] if producers else None,
                elevation_min=elevation_min,
                elevation_max=elevation_max,
                process=processes[0] if processes else None,
                variety=", ".join(varietals) if varietals else None,
            )
        ]

    def _to_country_code(self, name: str) -> str | None:
        """Map a country name to its alpha-2 code (fallback: upper-cased name)."""
        if not name:
            return None
        code = _country_name_to_alpha2().get(name.strip().lower())
        return code or name.strip().upper()

    def _strip_html(self, text: str) -> str:
        """Strip HTML tags and entities, collapsing whitespace."""
        text = re.sub(r"<[^>]+>", " ", text or "")
        text = html.unescape(text)
        return re.sub(r"\s+", " ", text).strip()

    async def _create_diffjson_update_from_api_product(self, product: dict, output_dir: Path) -> bool:
        """Create a diffjson update from Store API product data.

        Args:
            product: Product data from the API

        Returns:
            True if diffjson was created successfully
        """
        try:
            product_url = self._product_url(product)
            if not product_url:
                return False

            prices = product.get("prices", {})
            currency = (prices.get("currency_code") or "EUR").upper()
            price = _minor_unit_price(
                (prices.get("price_range") or {}).get("min_amount") or prices.get("price"),
                prices.get("currency_minor_unit"),
            )

            update_data: dict = {
                "url": product_url,
                "in_stock": product.get("is_in_stock", False),
                "scraped_at": datetime.now(timezone.utc).isoformat(),
                "scraper_version": "3.0",
            }
            name = (product.get("name") or "").strip()
            if name:
                update_data["name"] = name
            if price is not None:
                update_data["price"] = price
                update_data["currency"] = currency

            # Validate using Pydantic schema (for error checking)
            CoffeeBeanDiffUpdate.model_validate(update_data)

            # Save diffjson file
            session_datetime = self.session_datetime or datetime.now().strftime("%Y%m%d")
            bean_dir = output_dir / "roasters" / self._get_roaster_dir_name() / session_datetime
            bean_dir.mkdir(parents=True, exist_ok=True)

            filename = self._generate_diffjson_filename(product_url)
            output_path = bean_dir / f"{filename}.diffjson"

            # Save diffjson file - use dict directly to avoid Pydantic serialization issues
            with open(output_path, "w") as f:
                json.dump(update_data, f, ensure_ascii=False, indent=2)

            logger.debug(f"Created diffjson update: {output_path}")
            return True

        except Exception as e:
            logger.warning(f"Failed to create diffjson update for product: {e}")
            return False

    async def _create_api_based_diffjson_updates(
        self, products: list[dict], current_product_urls: list[str], output_dir: Path, force_full_update: bool = False
    ) -> tuple[int, int]:
        """Create diffjson stock updates using Store API product data.

        This method leverages the rich API data to create more accurate diffjson updates
        compared to the base class method which only has URLs.

        Args:
            products: Product data from the API
            current_product_urls: List of URLs currently available
            output_dir: Base output directory
            force_full_update: If True, skip diffjson creation

        Returns:
            Tuple of (in_stock_count, out_of_stock_count)
        """
        if force_full_update:
            logger.info("Force full update mode - skipping diffjson creation")
            return 0, 0

        # Load existing beans from all sessions
        self._load_existing_beans_from_all_sessions(output_dir)

        # Create diffjson updates for products that were previously scraped
        in_stock_count = 0
        for product in products:
            product_url = self._product_url(product)
            if not product_url:
                continue
            if self._is_bean_already_scraped_historically(product_url):
                if await self._create_diffjson_update_from_api_product(product, output_dir):
                    in_stock_count += 1

        # Create out-of-stock updates for products no longer available,
        # unless a listing fetch failed this session (network error, 404,
        # layout change) — in that case "not found" is untrustworthy and
        # marking the catalogue out of stock would poison the database.
        out_of_stock_count = 0
        if self._failed_listing_urls:
            msg = (
                f"Skipped out-of-stock updates: listing fetch failed for "
                f"{len(self._failed_listing_urls)} store URL(s): {self._failed_listing_urls}"
            )
            logger.warning(msg)
            if self.session:
                self.session.add_error(msg)
        else:
            out_of_stock_count = await self._create_out_of_stock_updates_from_api(current_product_urls, output_dir)

        logger.info(f"Created {in_stock_count} in-stock and {out_of_stock_count} out-of-stock diffjson updates")
        return in_stock_count, out_of_stock_count

    async def _create_out_of_stock_updates_from_api(self, current_urls: list[str], output_dir: Path) -> int:
        """Create diffjson files for products that are no longer available.

        Args:
            current_urls: List of URLs currently available on the website
            output_dir: Base output directory

        Returns:
            Number of out-of-stock updates created
        """
        # Find existing beans that are no longer in the current product list
        current_url_set = {self._normalize_url(u) for u in current_urls}
        out_of_stock_urls = [
            url for url in self._all_sessions_bean_files if self._normalize_url(url) not in current_url_set
        ]

        if not out_of_stock_urls:
            return 0

        logger.info(f"Creating out-of-stock updates for {len(out_of_stock_urls)} products")

        session_datetime = self.session_datetime or datetime.now().strftime("%Y%m%d")
        bean_dir = output_dir / "roasters" / self._get_roaster_dir_name() / session_datetime
        bean_dir.mkdir(parents=True, exist_ok=True)

        created_count = 0
        for url in out_of_stock_urls:
            try:
                # Create diffjson update indicating the product is out of stock
                update_data = {
                    "url": str(url),
                    "in_stock": False,
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                    "scraper_version": "3.0",
                }

                # Validate using Pydantic schema (for error checking)
                CoffeeBeanDiffUpdate.model_validate(update_data)

                # Generate filename based on URL
                filename = self._generate_diffjson_filename(str(url))
                output_path = bean_dir / f"{filename}_out_of_stock.diffjson"

                # Save diffjson file
                with open(output_path, "w") as f:
                    json.dump(update_data, f, indent=2)

                logger.debug(f"Created out-of-stock diffjson: {output_path}")
                created_count += 1

            except Exception as e:
                logger.warning(f"Failed to create out-of-stock diffjson for {url}: {e}")
                continue

        return created_count

    async def _extract_product_urls_from_store(self, store_url: str) -> list[str]:
        """Not implemented for DAK Coffee Roasters"""
        raise NotImplementedError("Not implemented for DAK Coffee Roasters")
