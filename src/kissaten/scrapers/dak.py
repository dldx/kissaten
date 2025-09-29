"""DAK Coffee Roasters scraper using their API endpoint.

This scraper uses DAK Coffee's API endpoint instead of traditional HTML scraping,
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from pydantic import HttpUrl

from ..ai.extractor import CoffeeDataExtractor
from ..schemas import CoffeeBean, CoffeeBeanDiffUpdate
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


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
    """Scraper for DAK Coffee Roasters using their API endpoint."""

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
        # Initialize AI extractor
        self.extractor = CoffeeDataExtractor()

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Note: This method is not used for API-based scraping but is required by the base class.

        Returns:
            Empty list since we use API endpoint directly
        """
        return []

    async def scrape(
        self,
        output_dir=None,
        force_full_update: bool = False,
        create_diffjson_updates: bool = True
    ) -> list[CoffeeBean]:
        """Scrape coffee beans from DAK Coffee Roasters using their API endpoint.

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

            # Call the API endpoint
            api_url = "https://www.dakcoffeeroasters.com/api/products/all?isActive=true"
            logger.info(f"Fetching data from DAK Coffee API: {api_url}")

            response = await self.client.get(api_url)
            response.raise_for_status()
            data = response.json()

            products = data.get("products", [])
            logger.info(f"Found {len(products)} products from DAK Coffee API")

            session.requests_made += 1

            # Extract all current product URLs for diffjson processing
            current_product_urls = []
            for product in products:
                if product.get("type") == "coffee":
                    slug = product.get("slug", "")
                    if slug:
                        product_url = f"https://www.dakcoffeeroasters.com/shop/coffee/{slug}"
                        current_product_urls.append(product_url)

            # Create diffjson stock updates for existing products if enabled
            in_stock_count = 0
            out_of_stock_count = 0
            if create_diffjson_updates:
                in_stock_count, out_of_stock_count = await self._create_api_based_diffjson_updates(
                    products, current_product_urls, output_dir, force_full_update
                )

            # Process each product
            for product in products:
                try:
                    # Skip non-coffee products
                    if product.get("type") != "coffee":
                        continue

                    # Build product URL
                    slug = product.get("slug", "")
                    if slug:
                        product_url = f"https://www.dakcoffeeroasters.com/shop/coffee/{slug}"
                    else:
                        product_url = "https://www.dakcoffeeroasters.com"

                    # Skip if already scraped in this session
                    if self._is_bean_already_scraped_in_session(product_url):
                        product_name = self._get_localized_text(product.get("name", {}))
                        logger.debug(f"Skipping already scraped product: {product_name}")
                        continue

                    # If not forcing full update and diffjson is enabled, skip existing products
                    # (they've already been handled by diffjson updates)
                    if not force_full_update and create_diffjson_updates:
                        if self._is_bean_already_scraped_historically(product_url):
                            product_name = self._get_localized_text(product.get("name", {}))
                            logger.debug(f"Skipping existing product (handled by diffjson): {product_name}")
                            continue

                    # Parse the product using AI extractor
                    coffee_bean = await self._parse_product_with_ai(product)

                    if coffee_bean:
                        coffee_beans.append(coffee_bean)
                        self._mark_bean_as_scraped(product_url)

                except Exception as e:
                    product_name = self._get_localized_text(product.get("name", {}))
                    logger.warning(f"Error processing product {product_name}: {e}")
                    session.add_error(f"Error processing product: {e}")
                    continue

            # Log summary
            total_products = len([p for p in products if p.get("type") == "coffee"])
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
            session.beans_found = len(coffee_beans)
            session.beans_processed = len(coffee_beans)

            self.end_session(success=True)
            return coffee_beans

        except Exception as e:
            logger.error(f"Error fetching data from DAK Coffee API: {e}")
            session.add_error(f"API error: {e}")
            self.end_session(success=False)
            return []

    async def _parse_product_with_ai(self, product: dict) -> CoffeeBean | None:
        """Parse a product from the API response using AI extractor.

        Args:
            product: Product data from the API

        Returns:
            CoffeeBean object or None if parsing fails
        """
        try:
            # Skip non-coffee products
            if product.get("type") != "coffee":
                return None

            # Build product URL
            slug = product.get("slug", "")
            if slug:
                product_url = f"https://www.dakcoffeeroasters.com/shop/coffee/{slug}"
            else:
                return None

            # Use AI extractor to parse the product
            coffee_bean = await self.extractor.extract_coffee_data(
                html_content=json.dumps(product),
                product_url=product_url,
                use_optimized_mode=False,
                translate_to_english=False
            )

            if not coffee_bean:
                return None

            # Override URL and image URL with our API-derived values
            coffee_bean.url = HttpUrl(product_url)

            # Set image URL from API data
            if product.get("images", {}).get("main"):
                image_url = f"https://res.cloudinary.com/dak-coffee-roasters/image/upload/f_auto,q_auto,c_scale//Products/Mains/{product['images']['main']}"
                coffee_bean.image_url = HttpUrl(image_url)

            # Ensure roaster name is correct
            coffee_bean.roaster = "DAK Coffee Roasters"
            coffee_bean.description = self._get_localized_text(product.get("short", {}))

            # Set stock status from API
            coffee_bean.in_stock = product.get("isActive", False)

            # Set raw data
            coffee_bean.raw_data = json.dumps(product, ensure_ascii=False)

            return coffee_bean

        except Exception as e:
            logger.error(f"Error parsing product with AI: {e}")
            return None

    def _get_localized_text(self, text_obj: dict) -> str:
        """Extract localized text, preferring English.

        Args:
            text_obj: Dictionary with language codes as keys

        Returns:
            Localized text string
        """
        if not isinstance(text_obj, dict):
            return str(text_obj).strip() if text_obj else ""

        # Prefer English, then Dutch, then French, then any available
        for lang in ["en", "nl", "fr"]:
            if lang in text_obj and text_obj[lang]:
                return str(text_obj[lang]).strip()

        # Fallback to any available text
        for value in text_obj.values():
            if value:
                return str(value).strip()

        return ""

    def _extract_price_info(self, price_list: list) -> dict:
        """Extract price information from the price list.

        Args:
            price_list: List of price objects

        Returns:
            Dictionary with price, currency, and weight information
        """
        if not price_list:
            return {}

        # Prefer EUR pricing, fallback to first available
        eur_price = None
        fallback_price = None

        for price_obj in price_list:
            base = price_obj.get("base", {})
            currency = base.get("currency", "").upper()

            if currency == "EUR":
                eur_price = price_obj
                break
            elif not fallback_price:
                fallback_price = price_obj

        price_obj = eur_price or fallback_price
        if not price_obj:
            return {}

        base = price_obj.get("base", {})
        increments = price_obj.get("increments", [])

        # Get base price info
        price = base.get("value")
        currency = base.get("currency", "EUR").upper()

        # Get weight from first increment (usually the base size)
        weight = ""
        if increments:
            weight = increments[0].get("option", "")

        return {
            "price": price,
            "currency": currency,
            "weight": weight,
        }

    async def _create_diffjson_update_from_api_product(self, product: dict, output_dir: Path) -> bool:
        """Create a diffjson update from API product data.

        Args:
            product: Product data from the API
            output_dir: Output directory

        Returns:
            True if diffjson was created successfully
        """
        try:
            # Build product URL
            slug = product.get("slug", "")
            if slug:
                product_url = f"https://www.dakcoffeeroasters.com/shop/coffee/{slug}"
            else:
                return False

            # Extract basic fields that might have changed
            name = self._get_localized_text(product.get("name", {}))
            price_info = self._extract_price_info(product.get("price", []))
            is_active = product.get("isActive", False)

            # Create diffjson update
            update_data = {
                "url": product_url,
                "in_stock": is_active,
                "scraped_at": datetime.now(timezone.utc).isoformat(),
                "scraper_version": "3.0",
            }

            # Add optional fields if they have values
            if name:
                update_data["name"] = name
            if price_info.get("price"):
                update_data["price"] = price_info.get("price")
            if price_info.get("currency"):
                update_data["currency"] = price_info.get("currency", "EUR")

            # Validate using Pydantic schema (for error checking)
            CoffeeBeanDiffUpdate.model_validate(update_data)

            # Save diffjson file
            session_datetime = self.session_datetime or datetime.now().strftime("%Y%m%d")
            bean_dir = output_dir / "roasters" / self.roaster_name.replace(" ", "_").lower() / session_datetime
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
        self,
        products: list[dict],
        current_product_urls: list[str],
        output_dir: Path,
        force_full_update: bool = False
    ) -> tuple[int, int]:
        """Create diffjson stock updates using API product data.

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

        # Create diffjson updates for existing in-stock products
        in_stock_count = 0
        for product in products:
            if product.get("type") != "coffee":
                continue

            slug = product.get("slug", "")
            if not slug:
                continue

            product_url = f"https://www.dakcoffeeroasters.com/shop/coffee/{slug}"

            # Only create diffjson for products that were previously scraped
            if self._is_bean_already_scraped_historically(product_url):
                if await self._create_diffjson_update_from_api_product(product, output_dir):
                    in_stock_count += 1

        # Create out-of-stock updates for products no longer available
        out_of_stock_count = await self._create_out_of_stock_updates_from_api(
            current_product_urls, output_dir
        )

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
        current_url_set = set(current_urls)
        out_of_stock_urls = []

        for existing_url in self._all_sessions_bean_files:
            if existing_url not in current_url_set:
                out_of_stock_urls.append(existing_url)

        if not out_of_stock_urls:
            return 0

        logger.info(f"Creating out-of-stock updates for {len(out_of_stock_urls)} products")

        session_datetime = self.session_datetime or datetime.now().strftime("%Y%m%d")
        bean_dir = output_dir / "roasters" / self.roaster_name.replace(" ", "_").lower() / session_datetime
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