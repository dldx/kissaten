"""Dak Coffee Roasters scraper implementation using their API endpoint."""

import json
import logging

from pydantic import HttpUrl

from ..ai import CoffeeDataExtractor
from ..schemas import CoffeeBean
from .base import BaseScraper
from .registry import register_scraper

logger = logging.getLogger(__name__)


@register_scraper(
    name="dak",
    display_name="Dak Coffee Roasters",
    roaster_name="Dak Coffee Roasters",
    website="dakcoffeeroasters.com",
    description="Amsterdam-based specialty coffee roaster",
    requires_api_key=False,  # No longer need API key since we're using their API
    currency="EUR",
    country="Netherlands",
    status="available",
)
class DakCoffeeScraper(BaseScraper):
    """Scraper for Dak Coffee Roasters (dakcoffeeroasters.com) using their API endpoint."""

    def __init__(self, api_key: str | None = None):
        """Initialize Dak Coffee scraper.

        Args:
            api_key: Gemini API key for AI extraction.
        """
        super().__init__(
            roaster_name="Dak Coffee Roasters",
            base_url="https://www.dakcoffeeroasters.com",
            rate_limit_delay=1.0,  # API calls can be faster than web scraping
            max_retries=3,
            timeout=30.0,
        )

        # Initialize AI extractor
        self.ai_extractor = None
        try:
            self.ai_extractor = CoffeeDataExtractor(api_key=api_key)
        except Exception as e:
            logger.warning(f"AI extractor not available: {e} - falling back to basic extraction")

    def get_store_urls(self) -> list[str]:
        """Get store URLs to scrape.

        Note: This method is not used for API-based scraping but is required by the base class.

        Returns:
            Empty list since we use API endpoint directly
        """
        return []

    async def scrape(self, output_dir=None) -> list[CoffeeBean]:
        """Scrape coffee beans from Dak Coffee Roasters using their API endpoint with AI extraction.

        Args:
            output_dir: Output directory for saving files (optional)

        Returns:
            List of CoffeeBean objects
        """
        # Start scraping session
        session = self.start_session()
        coffee_beans = []

        try:
            # Load existing beans for this session to avoid re-scraping
            from pathlib import Path

            if output_dir is None:
                output_dir = Path("data")
            else:
                output_dir = Path(output_dir)

            self._load_existing_beans_for_session(output_dir)

            api_url = "https://www.dakcoffeeroasters.com/api/products/all?isActive=true"

            response = await self.client.get(api_url)
            response.raise_for_status()
            data = response.json()

            products = data.get("products", [])
            logger.info(f"Found {len(products)} products from DAK Coffee API")

            # Track session stats
            session.requests_made += 1  # API call

            # Process each product with AI if available
            for product in products:
                try:
                    # Skip non-coffee products
                    if product.get("type") != "coffee":
                        continue

                    # Build product URL to check if already scraped
                    slug = product.get("slug", "")
                    if slug:
                        product_url = f"https://www.dakcoffeeroasters.com/shop/coffee/{slug}"
                    else:
                        product_url = "https://www.dakcoffeeroasters.com"

                    # Skip if already scraped in this session
                    if self._is_bean_already_scraped(product_url):
                        product_name = product.get("name", {}).get("en", "Unknown")
                        logger.debug(f"Skipping already scraped product: {product_name}")
                        continue

                    # Use AI extraction if available, otherwise fallback to basic parsing
                    if self.ai_extractor:
                        coffee_bean = await self._extract_bean_with_ai(product)
                    else:
                        coffee_bean = self._parse_product(product)

                    if coffee_bean:
                        coffee_beans.append(coffee_bean)
                        # Mark as scraped to avoid reprocessing
                        self._mark_bean_as_scraped(product_url)

                except Exception as e:
                    logger.warning(f"Error processing product {product.get('name', {}).get('en', 'Unknown')}: {e}")
                    session.add_error(f"Error processing product: {e}")
                    continue

            # Log summary of processing
            total_products = len([p for p in products if p.get("type") == "coffee"])
            skipped_count = total_products - len(coffee_beans)
            if skipped_count > 0:
                logger.info(f"Skipped {skipped_count} already scraped products from today's session")
            logger.info(f"Successfully processed {len(coffee_beans)} coffee beans")

            # Save beans to individual JSON files
            if coffee_beans:
                saved_files = self.save_beans_individually(coffee_beans, output_dir)
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

    def _parse_product(self, product: dict) -> CoffeeBean | None:
        """Parse a product from the API response into a CoffeeBean object.

        Args:
            product: Product data from the API

        Returns:
            CoffeeBean object or None if parsing fails
        """
        try:
            # Skip non-coffee products
            if product.get("type") != "coffee":
                return None

            # Extract basic info
            name = self._get_localized_text(product.get("name", {}))
            if not name:
                return None

            description = self._get_localized_text(product.get("description", {}))
            short_description = self._get_localized_text(product.get("short", {}))

            # Extract origin information
            origin_data = product.get("origin", {})
            country = self._get_localized_text(origin_data.get("country", {}))
            region = origin_data.get("region", "")
            altitude_str = origin_data.get("altitude", "")
            variety = origin_data.get("variety", "")
            lot = origin_data.get("lot", "")

            # Parse altitude
            elevation = 0
            if altitude_str:
                # Extract numeric part from strings like "2000m" or "1900m"
                altitude_num = "".join(filter(str.isdigit, str(altitude_str)))
                if altitude_num:
                    elevation = int(altitude_num)

            # Extract process and tasting notes
            process = self._get_localized_text(origin_data.get("process", {}))
            tasting_notes_str = self._get_localized_text(origin_data.get("tasting_notes", {}))

            # Parse tasting notes into list
            tasting_notes = []
            if tasting_notes_str:
                # Split by common delimiters
                notes = tasting_notes_str.replace(",", ";").split(";")
                tasting_notes = [note.strip() for note in notes if note.strip()]

            # Extract harvest/producer information
            harvest_info = self._get_localized_text(product.get("harvest", {}))

            # Extract price information
            price_info = self._extract_price_info(product.get("price", []))

            # Build URL
            slug = product.get("slug", "")
            if slug:
                url = f"https://www.dakcoffeeroasters.com/shop/coffee/{slug}"
            else:
                url = "https://www.dakcoffeeroasters.com"

            # Extract producer name from harvest info (try to find a name pattern)
            producer = None
            if harvest_info:
                # Look for common producer patterns in the harvest text
                import re

                # Look for patterns like "Producer: Name" or names in the text
                name_patterns = [
                    r"producer[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
                    r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+is\s+a",
                    r"from\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
                ]
                for pattern in name_patterns:
                    match = re.search(pattern, harvest_info, re.IGNORECASE)
                    if match:
                        producer = match.group(1).strip()
                        # Truncate if too long for schema validation
                        if len(producer) > 100:
                            producer = producer[:97] + "..."
                        break

            # Create Origin object
            from ..schemas.coffee_bean import Bean

            origin = Bean(
                country=country,
                region=region,
                producer=producer,
                farm=lot if lot else None,
                elevation=elevation,
            )

            # Parse weight from price info
            weight = None
            weight_str = price_info.get("weight", "")
            if weight_str:
                # Extract numeric part from strings like "250g" or "1kg"
                weight_num = "".join(filter(str.isdigit, weight_str))
                if weight_num:
                    weight = int(weight_num)
                    # Convert kg to grams
                    if "kg" in weight_str.lower():
                        weight *= 1000

            return CoffeeBean(
                name=name,
                roaster="Dak Coffee Roasters",
                url=HttpUrl(url),
                origin=origin,
                is_single_origin=True,  # Most specialty coffee is single origin
                process=process,
                variety=variety,
                harvest_date=None,  # Not provided in API
                price_paid_for_green_coffee=None,  # Not provided in API
                currency_of_price_paid_for_green_coffee=None,  # Not provided in API
                roast_level=None,  # Could map from roastOptions but not clear mapping
                weight=weight,
                price=price_info.get("price"),
                currency=price_info.get("currency", "EUR"),
                is_decaf=False,  # Assume not decaf unless specified
                tasting_notes=tasting_notes,
                description=(
                    f"{short_description}\n\n{description}".strip() if short_description or description else None
                ),
                in_stock=product.get("isActive", False),
                scraper_version="2.0",  # Updated version for API-based scraper
                raw_data=str(product),  # Store raw API response for debugging
            )

        except Exception as e:
            logger.error(f"Error parsing product: {e}")
            return None

    def _get_localized_text(self, text_obj: dict) -> str:
        """Extract localized text, preferring English.

        Args:
            text_obj: Dictionary with language codes as keys

        Returns:
            Localized text string
        """
        if not isinstance(text_obj, dict):
            return str(text_obj) if text_obj else ""

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

    async def _extract_bean_with_ai(self, product: dict) -> CoffeeBean | None:
        """Extract coffee bean data using AI from API JSON data.

        Args:
            product: Product data from the API

        Returns:
            CoffeeBean object or None if extraction fails
        """
        try:
            # Check if AI extractor is available
            if not self.ai_extractor:
                logger.warning("AI extractor not available, falling back to basic parsing")
                return self._parse_product(product)

            # Build product URL
            slug = product.get("slug", "")
            if slug:
                product_url = f"https://www.dakcoffeeroasters.com/shop/coffee/{slug}"
            else:
                product_url = "https://www.dakcoffeeroasters.com"

            # Convert product data to a structured format for AI processing
            formatted_product_data = f"""
Product Data from DAK Coffee Roasters API:

Name: {self._get_localized_text(product.get("name", {}))}
Type: {product.get("type", "")}
Description: {self._get_localized_text(product.get("description", {}))}
Short Description: {self._get_localized_text(product.get("short", {}))}

Origin Information:
- Country: {self._get_localized_text(product.get("origin", {}).get("country", {}))}
- Region: {product.get("origin", {}).get("region", "")}
- Altitude: {product.get("origin", {}).get("altitude", "")}
- Variety: {product.get("origin", {}).get("variety", "")}
- Lot: {product.get("origin", {}).get("lot", "")}
- Process: {self._get_localized_text(product.get("origin", {}).get("process", {}))}
- Tasting Notes: {self._get_localized_text(product.get("origin", {}).get("tasting_notes", {}))}

Harvest Information: {self._get_localized_text(product.get("harvest", {}))}

Pricing: {json.dumps(product.get("price", []), indent=2)}

Active: {product.get("isActive", False)}
Slug: {slug}

Full JSON Data:
{json.dumps(product, indent=2)}
"""

            # Use AI extractor to process the formatted data
            bean = await self.ai_extractor.extract_coffee_data(
                html_content=formatted_product_data,
                product_url=product_url,
                screenshot_bytes=None,
                use_optimized_mode=False,
            )

            if bean:
                # Override AI-generated fields with actual API data to preserve accuracy and order

                # Override description with actual API data including harvest notes
                description = self._get_localized_text(product.get("description", {}))
                short_description = self._get_localized_text(product.get("short", {}))
                harvest_notes = self._get_localized_text(product.get("harvest", {}))

                # Combine descriptions properly including harvest information
                description_parts = []
                if short_description:
                    description_parts.append(short_description.strip())
                if description:
                    description_parts.append(description.strip())
                if harvest_notes:
                    description_parts.append(f"Harvest Information: {harvest_notes.strip()}")

                if description_parts:
                    bean.description = "\n\n".join(description_parts)
                else:
                    bean.description = None

                # Override origin fields with actual API data
                origin_data = product.get("origin", {})
                if bean.origin:
                    # Override region
                    bean.origin.region = origin_data.get("region", "") or None

                    # Override variety
                    bean.variety = origin_data.get("variety", "") or None

                # Override process with actual API data
                process = self._get_localized_text(origin_data.get("process", {}))
                bean.process = process or None

                # Override tasting notes with actual API data to preserve order
                tasting_notes_str = self._get_localized_text(origin_data.get("tasting_notes", {}))
                if tasting_notes_str:
                    # Split by common delimiters and preserve order
                    notes = tasting_notes_str.replace(",", ";").split(";")
                    bean.tasting_notes = [note.strip() for note in notes if note.strip()]
                else:
                    bean.tasting_notes = []

                logger.debug(f"AI successfully extracted: {bean.name}")
                return bean
            else:
                logger.warning(
                    f"AI extraction returned None for product: {product.get('name', {}).get('en', 'Unknown')}"
                )
                return None

        except Exception as e:
            logger.error(f"AI extraction failed for product: {e}")
            return None
