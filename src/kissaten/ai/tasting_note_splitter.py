"""Tasting note splitting using Gemini 2.5 Flash Lite."""

import logging
import os
from typing import List

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.gemini import GeminiModelSettings

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class TastingNotesSplit(BaseModel):
    """Result of splitting a long tasting note string into individual notes."""
    notes: List[str] = Field(description="List of individual flavor notes extracted from the input text")

class TastingNoteSplitter:
    """Splits long, descriptive tasting notes into individual flavor notes using AI."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key required. Set GOOGLE_API_KEY environment variable.")

        self.agent = Agent(
            "gemini-2.5-flash-lite",
            output_type=TastingNotesSplit,
            system_prompt=self._get_system_prompt(),
            model_settings=GeminiModelSettings(gemini_thinking_config={"thinking_budget": 0}),
        )

    def _get_system_prompt(self) -> str:
        return """
You are an expert coffee flavor analyst. Your task is to take a long, descriptive tasting note string 
and split it into a list of individual, concise flavor notes.

GUIDELINES:
1. Extract specific flavor words and short phrases (e.g., "Raspberry", "Caramel Sweetness", "Lime Acidity").
2. Remove filler words, marketing language, and narrative elements (e.g., "Super juicy mouthfeel with fruity notes of...", "The espresso roast comes with...").
3. Normalize the notes to Title Case.
4. If the input already contains multiple notes separated by punctuation, preserve them as separate items.
5. Focus on the actual flavors and tactical descriptions of the cup profile.
6. If a note mentions a specific type of acidity or sweetness, keep that context (e.g., "Citrus Acidity", "Honey Sweetness").
7. In some cases, the input may be a flavour description that is not a list of notes. In these cases, return the input as a single item in the list.

EXAMPLES:
Input: "Super Juicy Mouthfeel With Fruity Notes Of Raspberry, Red Apple And A Lime Acidity. The Espresso Roast Comes With A Bold Caramel Sweetness As Well."
Output: ["Raspberry", "Red Apple", "Lime Acidity", "Caramel Sweetness", "Super Juicy Mouthfeel"]

Input: "Notes of dark chocolate and roasted hazelnuts with a hint of vanilla."
Output: ["Dark Chocolate", "Roasted Hazelnuts", "Vanilla"]

Input: "Bright and floral with jasmine and bergamot."
Output: ["Bright", "Floral", "Jasmine", "Bergamot"]

Input: "Fizzy Watermelon"
Output: ["Fizzy Watermelon"]
Reason: Fizzy is an adjective modifying watermelon, not a separate flavour note.
"""

    async def split_notes(self, text: str) -> List[str]:
        """Split a long tasting note string into individual notes.
        
        Args:
            text: The long tasting note string to split.
            
        Returns:
            List of individual tasting notes.
        """
        if not text or len(text) < 10:
            return [text.strip().title()] if text.strip() else []

        try:
            result = await self.agent.run(f"Split these tasting notes: {text}")
            return result.output.notes
        except Exception as e:
            logger.error(f"Error splitting tasting notes: {e}")
            # Fallback: just return the original text wrapped in a list
            return [text.strip().title()]
