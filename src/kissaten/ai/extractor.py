"""AI-powered coffee data extraction using Gemini and PydanticAI."""

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
logfire.configure()
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
- name: The coffee product name (e.g., "Bungoma AA", "Luz Helena")
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
  * elevation: Elevation in meters (0-3000m, use 0 if unknown)
  * latitude: Latitude coordinate (-90 to 90, only if explicitly stated, do not guess)
  * longitude: Longitude coordinate (-180 to 180, only if explicitly stated, do not guess)
  * process: Processing method (e.g., "Natural", "Washed", "Honey")
  * variety: Coffee variety (e.g., "Catuai", "Bourbon") - only if specific variety mentioned
  * harvest_date: Harvest date (must be between 2020 and present, use earliest date if range given)

- is_single_origin: Boolean - true if coffee is from a single origin, false if it's a blend
- price_paid_for_green_coffee: Price paid for 1kg of green coffee if mentioned
- currency_of_price_paid_for_green_coffee: Currency of green coffee price if mentioned

PRODUCT DETAILS:
- roast_level: Must be one of: "Light", "Medium-Light", "Medium", "Medium-Dark", "Dark".
  Only set if explicitly stated - do not guess based on descriptions.
- roast_profile: "Espresso", "Filter", or "Omni" (if suitable for both espresso and filter)
- weight: Weight in grams (must be between 50g and 10kg if specified)
- price: Price in local currency (must be positive if specified)
- currency: Three-letter currency code (e.g., "GBP", "USD", "EUR") - defaults to "GBP"
- is_decaf: Boolean - true if decaffeinated, false otherwise (defaults to false)
- cupping_score: Score between 70-100, only if explicitly mentioned (do not estimate)

FLAVOR PROFILE:
- tasting_notes: List of flavor notes (e.g., ["Blackcurrant", "Raspberry", "Honey"]).
  Extract all tasting notes in the order they appear. These will be automatically cleaned,
  title-cased, and deduplicated. Extract full phrases if that's how they're presented.
- description: Complete product description/story (maximum 5000 characters).
  Extract the exact description from the product page, including narrative sections.

AVAILABILITY AND METADATA:
- in_stock: Boolean indicating availability (false if "out of stock" mentioned, null if unknown)
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
9. LANGUAGE: Translate non-English content to English
10. VALIDATION: Ensure all numeric fields meet their constraints (elevation 0-3000m, etc.)

Return a properly formatted CoffeeBean object with all extracted data following the schema validation rules.
"""

    async def extract_coffee_data(
        self,
        html_content: str,
        product_url: str,
        screenshot_bytes: bytes | None = None,
        use_optimized_mode: bool = False,
    ) -> CoffeeBean | None:
        """Extract coffee data from HTML content using AI with retry logic and screenshot fallback.

        Args:
            html_content: Raw HTML content of the coffee product page
            product_url: URL of the product page
            screenshot_bytes: Optional screenshot bytes for visual analysis
            use_optimized_mode: If True, use only gemini-2.5-flash with screenshots (for complex pages)

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

                logger.info(
                    f"AI extracted successfully on attempt {attempt}: {coffee_bean.name} from "
                    f"{', '.join(str(origin) for origin in coffee_bean.origins)}"
                )
                return coffee_bean

            except Exception as e:
                logger.warning(f"AI extraction attempt {attempt}/{max_attempts} failed for {product_url}: {e}")

                # If this was the last attempt, log as error and return None
                if attempt == max_attempts:
                    logger.error(f"All AI extraction attempts failed for {product_url}: {e}")
                    return None

                # Otherwise, continue to next attempt
                continue

        # This should never be reached, but included for completeness
        return None
