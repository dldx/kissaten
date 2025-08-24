"""AI-powered coffee data extraction using Gemini and PydanticAI."""

import logging
import os

from dotenv import load_dotenv
from pydantic import HttpUrl
from pydantic_ai import Agent

from ..schemas.coffee_bean import CoffeeBean

# Load environment variables from .env file
load_dotenv()


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
        )

        self.agent_full = Agent(
            "gemini-2.5-flash",
            output_type=CoffeeBean,
            system_prompt=self._get_system_prompt(),
        )

    def _get_system_prompt(self) -> str:
        """Get the system prompt for coffee data extraction."""
        return """
You are an expert coffee data extraction specialist. Your task is to extract structured
information about coffee beans from product pages.

Extract the following information from the provided HTML content:

REQUIRED FIELDS:
- name: The coffee product name (e.g., "Bungoma AA", "Luz Helena")
- roaster: The coffee roaster name (e.g., "Cartwheel Coffee", "Coborn Coffee")
- url: The product URL provided in the context

ORIGIN AND PROCESSING:
- origin: Country, region, farm, elevation if mentioned
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
- tasting_notes: List of flavor notes (e.g., ["Blackcurrant", "Raspberry", "Honey"])
- description: Product story or description (extract from "story" section if available)

AVAILABILITY:
- in_stock: Boolean indicating if product is available (false if "out of stock" mentioned)

METADATA:
- scraper_version: Set to "2.0"
- raw_data: Set to null

EXTRACTION GUIDELINES:
1. Be accurate and conservative - if information isn't clearly present, use null/None
2. For tasting notes, extract from patterns like "Word / Word / Word" or similar. Make sure to extract all the tasting notes and keep them in the same order as they appear in the text.
3. For origin, look for standalone country names after the product name
4. For prices, prefer the standard 250g option if multiple weights are available
5. Extract the story/description from narrative sections about the coffee
6. Process and variety information is often in structured sections

Return a properly formatted CoffeeBean object with all extracted data.
"""

    async def extract_coffee_data(self, html_content: str, product_url: str) -> CoffeeBean | None:
        """Extract coffee data from HTML content using AI with retry logic.

        Args:
            html_content: Raw HTML content of the coffee product page
            product_url: URL of the product page

        Returns:
            CoffeeBean object with extracted data or None if extraction fails
        """
        # Prepare the context for the AI
        context = f"""
Product URL: {product_url}

HTML Content:
{html_content}
"""

        # Retry logic: 3 attempts total
        # Attempts 1-2: Use gemini-2.5-flash-lite
        # Attempt 3: Use gemini-2.5-flash (full model)
        for attempt in range(1, 4):
            try:
                # Choose the agent based on attempt number
                if attempt <= 2:
                    agent = self.agent_lite
                    model_name = "gemini-2.5-flash-lite"
                else:
                    agent = self.agent_full
                    model_name = "gemini-2.5-flash"

                logger.debug(f"AI extraction attempt {attempt}/3 using {model_name} for {product_url}")

                # Run the AI extraction
                result = await agent.run(context)

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
                logger.warning(f"AI extraction attempt {attempt}/3 failed for {product_url}: {e}")

                # If this was the last attempt, log as error and return None
                if attempt == 3:
                    logger.error(f"All AI extraction attempts failed for {product_url}: {e}")
                    return None

                # Otherwise, continue to next attempt
                continue

        # This should never be reached, but included for completeness
        return None

