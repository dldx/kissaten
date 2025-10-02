"""AI-powered coffee data extraction using Gemini and PydanticAI."""

import asyncio
import datetime
import logging
import os

import logfire
from dotenv import load_dotenv
from pydantic import HttpUrl
from pydantic_ai import Agent, BinaryContent
from pydantic_ai.models.gemini import GeminiModelSettings

from ..schemas.coffee_bean import CoffeeBean

# Load environment variables from .env file
load_dotenv()

# Configure logfire
def scrubbing_callback(m: logfire.ScrubMatch):
    if m.path == ("attributes", "all_messages_events", 1, "content", 0) and m.pattern_match.group(0) == "Session":
        return m.value


logfire.configure(scrubbing=logfire.ScrubbingOptions(callback=scrubbing_callback))
logfire.instrument_pydantic_ai()


logger = logging.getLogger(__name__)


class CoffeeDataExtractor:
    """AI-powered coffee data extractor using Gemini 2.5 Flash."""

    def __init__(self, api_key: str | None = None):
        """Initialize the extractor.

        Args:
            api_key: Google API key. If None, will try to get from environment.
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Google API key required. Set GOOGLE_API_KEY environment variable or pass api_key parameter."
            )

        # Create the PydanticAI agents with different Gemini models
        self.agent_lite = Agent(
            "gemini-2.5-flash-lite",
            output_type=CoffeeBean,
            system_prompt=self._get_system_prompt(),
            model_settings=GeminiModelSettings(gemini_thinking_config={"thinking_budget": 0}),
        )

        self.agent_full = Agent(
            "gemini-2.5-flash",
            output_type=CoffeeBean,
            system_prompt=self._get_system_prompt(),
            model_settings=GeminiModelSettings(gemini_thinking_config={"thinking_budget": 0}),
        )

        # Translation agent for converting foreign language content to English
        self.agent_translator = Agent(
            "gemini-2.5-flash",
            output_type=CoffeeBean,
            system_prompt=self._get_translation_prompt(),
            model_settings=GeminiModelSettings(gemini_thinking_config={"thinking_budget": 0}),
        )

    def _get_system_prompt(self) -> str:
        """Get the system prompt for coffee data extraction."""
        return """
You are an expert coffee data extraction specialist. Your task is to extract structured
information about coffee beans from specialty coffee roaster product pages.

You may be provided with HTML content and/or a screenshot of the page. Use all available
information to extract the most accurate data possible. When a screenshot is provided,
use it to identify visual elements, prices, and product details that may not be clearly
structured in the HTML. Pay special attention to:
- Product images and visual layout
- Price information that may be stylized or in custom elements
- Tasting notes that may be displayed as graphics or styled text
- Product descriptions in hero sections or featured areas

Extract the following information from the provided content:

REQUIRED FIELDS:
- name: The coffee product name (e.g., "Bungoma AA", "Luz Helena"). Remove the roaster name if present, and details not specific to the coffee itself (e.g., "250g", "Filter Roast", "NEW").
- roaster: The coffee roaster name (e.g., "Cartwheel Coffee", "Coborn Coffee")
- url: The product URL provided in the context
- image_url: The main product image URL (look for high-quality product images, usually in <img> tags)

ORIGIN AND PROCESSING:
- origins: List of Bean objects representing each origin in the coffee. For single origin coffees,
  this should contain exactly one Bean. For blends, include multiple Bean objects.
  Each Bean object contains:
  * country: Two-letter country code (e.g., "CO", "KE", "BR") - will be auto-converted to uppercase
  * region: Region within the country (e.g., "Antioquia", "Huila") - will be auto-formatted to title case
  * producer: Producer name if mentioned (usually a person's name) - will be auto-formatted to title case
  * farm: Farm name if mentioned - will be auto-formatted to title case
  * elevation_min: Minimum elevation in meters (0-3000m, use 0 if unknown)
  * elevation_max: Maximum elevation in meters (0-3000m, use 0 if unknown)
  * latitude: Latitude coordinate (-90 to 90, only if explicitly stated, do not guess)
  * longitude: Longitude coordinate (-180 to 180, only if explicitly stated, do not guess)
  * process: Processing method (e.g., "Natural", "Washed", "Honey"). Try to be as specific as is mentioned.
  * variety: Coffee variety (e.g., "Catuai", "Bourbon") - only if specific variety mentioned
  * harvest_date: Harvest date (must be between 2020 and present, use earliest date if range given)

- is_single_origin: Boolean - true if coffee is from a single origin, false if it's a blend
- price_paid_for_green_coffee: Price paid for 1kg of green coffee if mentioned
- currency_of_price_paid_for_green_coffee: Currency of green coffee price if mentioned

PRODUCT DETAILS:
- roast_level: Must be one of: "Extra Light", "Light", "Medium-Light", "Medium", "Medium-Dark", "Dark".
  Only set if explicitly stated - do not guess based on descriptions.
- roast_profile: "Espresso", "Filter", or "Omni" (if suitable for both espresso and filter)
- price_options: List of PriceOption objects representing each price option. If there are multiple price options, include them all.
  Each PriceOption object contains:
  * weight: Weight in grams (must be between 50g and 10kg if specified)
  * price: Price in local currency (must be positive if specified). Pay special attention to decimal points, commas, and currency symbols.
- currency: Three-letter currency code (e.g., "GBP", "USD", "EUR") - defaults to "GBP"
- is_decaf: Boolean - true if decaffeinated, false otherwise (defaults to false)
- cupping_score: Score between 70-100, only if explicitly mentioned (do not estimate)

FLAVOR PROFILE:
- tasting_notes: List of flavor notes (e.g., ["Blackcurrant", "Raspberry", "Honey"]).
  Extract all tasting notes in the order they appear. These will be automatically cleaned,
  title-cased, and deduplicated. Extract full phrases if that's how they're presented.
- description: Complete product description/story (maximum 5000 characters). Remove any HTML tags.
  Extract the exact description from the product page, including narrative sections.

AVAILABILITY AND METADATA:
- in_stock: Boolean indicating availability (false if "out of stock" mentioned, true if no mention of being out of stock). Be sure to focus on availability of the specific weight you are extracting.
- scraped_at: Will be automatically set to current UTC timestamp
- scraper_version: Will be automatically set to "2.0"
- raw_data: Will be automatically set to null

EXTRACTION GUIDELINES:
1. BE CONSERVATIVE: If information isn't clearly present, use null/None rather than guessing
2. ORIGINS HANDLING:
   - For single origin: Create one Bean object with all available details
   - For blends: Create multiple Bean objects, one for each origin mentioned
   - Country codes will be auto-converted to uppercase (e.g., "co" → "CO")
   - Region, producer, farm names will be auto-formatted to title case
3. COORDINATE PRECISION: Only include latitude/longitude if explicitly stated with numbers
4. DATE VALIDATION: Harvest dates must be realistic (2020-present), use earliest if range given
5. WEIGHT/PRICE: Prefer standard 250g option if multiple sizes available
6. TASTING NOTES: Extract from patterns like "Word / Word / Word" or bullet points
7. ROAST LEVEL: Only use exact enum values, don't approximate or guess
8. DESCRIPTIONS: Include full product stories and narrative sections
9. ELEVATION: Use 0 for unknown values; if a range is given (e.g. "1400-1600m"), set elevation_min to 1400 and elevation_max to 1600
10. LANGUAGE: Translate non-English content to English
11. VALIDATION: Ensure all numeric fields meet their constraints (elevation_min/max 0-3000m, etc.)

Return a properly formatted CoffeeBean object with all extracted data following the schema validation rules.
"""

    def _get_translation_prompt(self) -> str:
        """Get the system prompt for translating coffee bean details to English."""
        return """
You are an expert translator specializing in coffee terminology and product descriptions.
Your task is to translate coffee bean information from any language to English while preserving
all technical coffee terms, origin names, and product details accurately.

You will receive a CoffeeBean object that may contain text in languages other than English.
Translate the following fields to English while keeping all other data unchanged:

FIELDS TO TRANSLATE:
- name: Coffee product name (preserve brand/origin names, translate descriptive parts)
- description: Product description/story (full translation to English)
- tasting_notes: Flavor notes (translate to standard English coffee terminology)
- origins[].region: Region names (translate to English if not proper nouns)
- origins[].producer: Producer names (usually keep as proper nouns)
- origins[].farm: Farm names (usually keep as proper nouns)
- origins[].process: Processing method (translate to standard English terms like "Natural", "Washed", "Honey")
- origins[].variety: Coffee variety (use standard English variety names)

TRANSLATION GUIDELINES:
1. PRESERVE TECHNICAL TERMS: Keep standard coffee terminology (e.g., "AA", "SHB", "EP")
2. PRESERVE PROPER NOUNS: Keep roaster names, farm names, producer names as they are
3. STANDARDIZE PROCESSING: Use standard English terms for processing methods
4. COFFEE VARIETIES: Use internationally recognized variety names in English
5. GEOGRAPHIC NAMES: Use English names for regions/provinces, keep local names for specific farms
6. TASTING NOTES: Use standard cupping terminology in English
7. PRESERVE STRUCTURE: Maintain the same CoffeeBean object structure
8. PRESERVE ALL METADATA: Keep all numeric fields, dates, URLs, etc. exactly as provided

EXAMPLES:
- "프릳츠 신커피" → "Fritz New Coffee" (translate descriptive part)
- "내츄럴 프로세싱" → "Natural" (standardize processing method)
- "초콜릿, 오렌지, 바닐라" → ["Chocolate", "Orange", "Vanilla"] (translate tasting notes)
- "콜롬비아 후일라" → region: "Huila" (use English region name)

Return the same CoffeeBean object with all non-English content translated to English.
"""

    def _extract_retry_delay_from_error(self, error: Exception) -> float | None:
        """Extract retry delay from API error response.

        Args:
            error: The exception from the API call

        Returns:
            Retry delay in seconds if found in error, None otherwise
        """
        error_str = str(error)

        # Try to extract retryDelay from the error message
        # Format: 'retryDelay': '48s'
        import re

        retry_match = re.search(r"'retryDelay':\s*'(\d+)s'", error_str)
        if retry_match:
            return float(retry_match.group(1))

        # Also check for other common patterns
        retry_match = re.search(r'"retryDelay":\s*"(\d+)s"', error_str)
        if retry_match:
            return float(retry_match.group(1))

        return None

    def _is_retryable_error(self, error: Exception) -> bool:
        """Check if an error is retryable (rate limits, temporary issues).

        Args:
            error: The exception from the API call

        Returns:
            True if the error should be retried, False otherwise
        """
        error_str = str(error).lower()

        # Rate limit errors (429)
        if "429" in error_str or "resource_exhausted" in error_str:
            return True

        # Temporary server errors (5xx)
        if any(code in error_str for code in ["500", "502", "503", "504"]):
            return True

        # Network/connection errors
        if any(keyword in error_str for keyword in ["connection", "timeout", "network", "temporarily unavailable"]):
            return True

        return False

    def _calculate_backoff_delay(self, attempt: int, base_delay: float = 1.0, max_delay: float = 60.0) -> float:
        """Calculate exponential backoff delay.

        Args:
            attempt: Current attempt number (1-based)
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds

        Returns:
            Delay in seconds
        """
        # Exponential backoff: base_delay * (2 ^ (attempt - 1))
        delay = base_delay * (2 ** (attempt - 1))
        return min(delay, max_delay)

    async def translate_to_english(self, coffee_bean: CoffeeBean) -> CoffeeBean | None:
        """Translate coffee bean details from any language to English.

        Args:
            coffee_bean: CoffeeBean object that may contain non-English content

        Returns:
            CoffeeBean object with all content translated to English, or None if translation fails
        """
        try:
            logger.debug(f"Translating coffee bean to English: {coffee_bean.name}")

            # Prepare context for translation
            context = f"""
Please translate the following coffee bean information to English:

Coffee Bean Data:
{coffee_bean.model_dump_json(indent=2)}

Translate all text fields to English while preserving the exact structure and all metadata.
"""

            # Run the translation with retry logic
            max_translation_attempts = 3
            for attempt in range(1, max_translation_attempts + 1):
                try:
                    result = await self.agent_translator.run(context)
                    translated_bean = result.output

                    # Preserve critical metadata that shouldn't change
                    translated_bean.url = coffee_bean.url
                    translated_bean.scraped_at = coffee_bean.scraped_at
                    translated_bean.scraper_version = coffee_bean.scraper_version
                    translated_bean.raw_data = coffee_bean.raw_data

                    logger.info(f"Successfully translated coffee bean: {coffee_bean.name} → {translated_bean.name}")
                    return translated_bean

                except Exception as e:
                    is_retryable = self._is_retryable_error(e)

                    logger.warning(
                        f"Translation attempt {attempt}/{max_translation_attempts} failed for {coffee_bean.name}: {e}"
                        + (f" (retryable: {is_retryable})" if is_retryable else " (not retryable)")
                    )

                    # If this was the last attempt, log as error and return None
                    if attempt == max_translation_attempts:
                        logger.error(f"All translation attempts failed for {coffee_bean.name}: {e}")
                        return None

                    # If it's not a retryable error, don't wait
                    if not is_retryable:
                        continue

                    # Calculate delay for retryable errors
                    retry_delay = self._extract_retry_delay_from_error(e)
                    if retry_delay is not None:
                        # Use the exact delay from the API response
                        delay = retry_delay
                        logger.info(f"Translation API requested {delay}s delay, waiting...")
                    else:
                        # Use exponential backoff
                        delay = self._calculate_backoff_delay(attempt)
                        logger.info(f"Translation using exponential backoff delay: {delay}s")

                    # Wait before retrying
                    await asyncio.sleep(delay)
                    continue

            return None

        except Exception as e:
            logger.error(f"Translation failed for {coffee_bean.name}: {e}")
            return None

    async def extract_coffee_data(
        self,
        html_content: str,
        product_url: str,
        screenshot_bytes: bytes | None = None,
        use_optimized_mode: bool = False,
        translate_to_english: bool = False,
    ) -> CoffeeBean | None:
        """Extract coffee data from HTML content using AI with retry logic and screenshot fallback.

        Args:
            html_content: Raw HTML content of the coffee product page
            product_url: URL of the product page
            screenshot_bytes: Optional screenshot bytes for visual analysis
            use_optimized_mode: If True, use only gemini-2.5-flash with screenshots (for complex pages)
            translate_to_english: If True, translate extracted content to English after extraction

        Returns:
            CoffeeBean object with extracted data or None if extraction fails
        """
        # Prepare the base context for the AI
        base_context = f"""
Product URL: {product_url}

HTML Content:
{html_content}
"""

        # Choose extraction strategy based on mode
        if use_optimized_mode:
            # Optimized mode: use only gemini-2.5-flash with screenshots (for complex pages)
            max_attempts = 3
            attempt_configs = [
                (self.agent_full, "gemini-2.5-flash", True),  # All attempts use full model + screenshot
                (self.agent_full, "gemini-2.5-flash", True),
                (self.agent_full, "gemini-2.5-flash", True),
            ]
        else:
            # Standard mode: progressive fallback (HTML-only → HTML+screenshot)
            max_attempts = 4
            attempt_configs = [
                (self.agent_lite, "gemini-2.5-flash-lite", False),  # HTML only
                (self.agent_lite, "gemini-2.5-flash-lite", False),  # HTML only
                (self.agent_full, "gemini-2.5-flash", False),  # HTML only
                (self.agent_full, "gemini-2.5-flash", True),  # HTML + screenshot
            ]

        for attempt in range(1, max_attempts + 1):
            try:
                agent, model_name, use_screenshot = attempt_configs[attempt - 1]

                logger.debug(
                    f"AI extraction attempt {attempt}/{max_attempts} using {model_name} for {product_url}"
                    + (" with screenshot" if use_screenshot and screenshot_bytes else "")
                    + (" [optimized mode]" if use_optimized_mode else "")
                )

                # Prepare input for the agent
                if use_screenshot and screenshot_bytes:
                    # Use screenshot + HTML for visual analysis
                    input_data = [
                        (
                            "Extract coffee bean information from this product page. "
                            "Use both the screenshot and HTML content below:\n\n" + base_context
                        ),
                        BinaryContent(data=screenshot_bytes, media_type="image/png"),
                    ]
                    logger.info(f"Using screenshot analysis for {product_url} (attempt {attempt})")
                else:
                    # Use HTML only
                    input_data = base_context
                    if use_screenshot and not screenshot_bytes:
                        logger.warning(f"No screenshot available for {product_url}, using HTML only")

                # Run the AI extraction
                result = await agent.run(input_data)

                # Get the extracted coffee bean data
                coffee_bean = result.output

                # Ensure required fields are set correctly
                coffee_bean.url = HttpUrl(product_url)
                coffee_bean.scraper_version = "2.0"
                coffee_bean.scraped_at = datetime.datetime.now(datetime.timezone.utc)
                # If in_stock is None, set it to True
                if coffee_bean.in_stock is None:
                    coffee_bean.in_stock = True

                logger.info(
                    f"AI extracted successfully on attempt {attempt}: {coffee_bean.name} from "
                    f"{', '.join(str(origin) for origin in coffee_bean.origins)}"
                )

                # Apply translation if requested
                if translate_to_english:
                    translated_bean = await self.translate_to_english(coffee_bean)
                    if translated_bean:
                        logger.info(f"Translation applied: {coffee_bean.name} → {translated_bean.name}")
                        return translated_bean
                    else:
                        logger.warning(f"Translation failed, returning original: {coffee_bean.name}")
                        return coffee_bean

                return coffee_bean

            except Exception as e:
                # Check if this is a retryable error
                is_retryable = self._is_retryable_error(e)

                logger.warning(
                    f"AI extraction attempt {attempt}/{max_attempts} failed for {product_url}: {e}"
                    + (f" (retryable: {is_retryable})" if is_retryable else " (not retryable)")
                )

                # If this was the last attempt, log as error and return None
                if attempt == max_attempts:
                    logger.error(f"All AI extraction attempts failed for {product_url}: {e}")
                    return None

                # If it's not a retryable error, don't wait
                if not is_retryable:
                    continue

                # Calculate delay for retryable errors
                retry_delay = self._extract_retry_delay_from_error(e)
                if retry_delay is not None:
                    # Use the exact delay from the API response
                    delay = retry_delay
                    logger.info(f"API requested {delay}s delay, waiting...")
                else:
                    # Use exponential backoff
                    delay = self._calculate_backoff_delay(attempt)
                    logger.info(f"Using exponential backoff delay: {delay}s")

                # Wait before retrying
                await asyncio.sleep(delay)
                continue

        # This should never be reached, but included for completeness
        return None
