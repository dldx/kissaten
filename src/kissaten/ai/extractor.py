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
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')
        if not self.api_key:
            raise ValueError(
                "Google API key required. Set GOOGLE_API_KEY environment variable "
                "or pass api_key parameter."
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
- origin: Country, region, farm, elevation if mentioned. Country should be a two letter code.
- producer: Producer name if mentioned. This is sometimes only hinted at in the product description
  so look out for person entities.
- process: Processing method (e.g., "Natural", "Washed", "Honey")
- variety: Coffee variety if mentioned (e.g., "Catuai", "Bourbon")
- harvest_date: Harvest date if mentioned
- price_paid_for_green_coffee: Price paid for 1kg of green coffee if mentioned
- currency_of_price_paid_for_green_coffee: Currency of price paid for green coffee if mentioned

PRODUCT DETAILS:
- roast_level: Roast level if mentioned (e.g., "Light", "Medium", "Dark")
- weight: Weight in grams if mentioned (extract from text like "250g")
- price: Price in GBP (extract from £ symbol, use the base price for 250g if multiple options)
- currency: Currency of the price in three letter code (e.g., "GBP", "USD", "EUR")

FLAVOR PROFILE:
- tasting_notes: List of flavor notes (e.g., ["Blackcurrant", "Raspberry", "Honey"]).
  Make sure to extract all the tasting notes and keep them in the same order as they appear in the text.
  Extract phrases or sentences if this is how they are presented.
- description: Product story or description (extract from "story" section if available).
  Try to extract the exact description from the product page.

AVAILABILITY:
- in_stock: Boolean indicating if product is available (false if "out of stock" mentioned)

METADATA:
- scraper_version: Set to "2.0"
- raw_data: Set to null

EXTRACTION GUIDELINES:
1. Be accurate and conservative - if information isn't clearly present, use null/None
2. For tasting notes, extract from patterns like "Word / Word / Word" or similar.
   Make sure to extract all the tasting notes and keep them in the same order as they appear in the text.
3. For origin, look for standalone country names after the product name
4. For prices, prefer the standard 250g option if multiple weights are available
5. Extract the story/description from narrative sections about the coffee
6. Process and variety information is often in structured sections

Return a properly formatted CoffeeBean object with all extracted data.
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
                    f"AI extracted successfully on attempt {attempt}: {coffee_bean.name} from {coffee_bean.origin}"
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

