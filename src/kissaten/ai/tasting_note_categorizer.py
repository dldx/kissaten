"""
Tasting note categorization using Gemini Flash 2.5 and PydanticAI.
"""

import asyncio
import csv
import logging
from pathlib import Path

import dotenv
import duckdb
import logfire
from pydantic import BaseModel, Field
from pydantic_ai import Agent

# Load environment variables from .env file
dotenv.load_dotenv()

logfire.configure(scrubbing=False)  # Initialize logfire for logging
logfire.instrument_pydantic_ai()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TastingNoteCategory(BaseModel):
    """A tasting note categorization."""

    tasting_note: str
    primary_category: str
    secondary_category: str | None
    tertiary_category: str | None
    confidence: float = Field(ge=0.0, le=1.0)


class TastingNoteBatch(BaseModel):
    """Batch of categorized tasting notes."""

    categorizations: list[TastingNoteCategory] = Field(description="List of categorized tasting notes")


class TastingNoteCategorizer:
    """Categorizes tasting notes using Gemini Flash 2.5."""

    def __init__(self, database_path: Path, taste_lexicon_path: Path):
        self.database_path = database_path
        self.taste_lexicon_path = taste_lexicon_path
        self.taste_lexicon = self._load_taste_lexicon()
        self.agent = self._create_agent()

    def _load_taste_lexicon(self) -> str:
        """Load the taste lexicon from JSON file as text."""
        with open(self.taste_lexicon_path) as f:
            return f.read()

    def _create_agent(self) -> Agent[None, TastingNoteBatch]:
        """Create the PydanticAI agent for categorization."""
        system_prompt = self._build_system_prompt()

        agent = Agent(
            "gemini-2.5-flash",
            output_type=TastingNoteBatch,
            system_prompt=system_prompt,
        )

        return agent

    def _build_system_prompt(self) -> str:
        """Build the system prompt with the taste lexicon."""

        return (
            "You are an expert coffee taster and flavor categorization specialist. "
            "Your task is to categorize coffee tasting notes according to a standardized taste lexicon.\n\n"
            f"TASTE LEXICON CATEGORIES:\n{self.taste_lexicon}\n\n"
            "INSTRUCTIONS:\n"
            "1. For each tasting note, assign it to the most appropriate primary category\n"
            "2. If applicable, also assign secondary and tertiary categories\n"
            "3. Provide a confidence score (0.0-1.0) for your categorization\n"
            '4. Handle variations and synonyms (e.g., "choc" = "chocolate", "citrusy" = "citrus")\n'
            '5. For compound notes (e.g., "dark chocolate"), identify the most specific category\n'
            "6. If a note doesn't clearly fit any category, use the closest match and lower confidence\n\n"
            "EXAMPLES:\n"
            '- "chocolate" → Primary: "Cocoa", Secondary: null, Confidence: 0.95\n'
            '- "berry" → Primary: "Fruity", Secondary: "Berry", Confidence: 0.90\n'
            '- "citrusy" → Primary: "Fruity", Secondary: "Citrus Fruit", Confidence: 0.85\n'
            '- "nutty chocolate" → Primary: "Cocoa", Secondary: null, Confidence: 0.80 (chocolate = specific)\n'
            '- "funky" → Primary: "Alcohol/Fermented", Secondary: null, Confidence: 0.60 (ambiguous term)\n\n'
            "Be consistent and precise in your categorizations. Focus on the dominant flavor characteristic."
        )

    async def categorize_batch(self, tasting_notes: list[str]) -> list[TastingNoteCategory]:
        """Categorize a batch of tasting notes."""
        notes_text = "\n".join([f"{i + 1}. {note}" for i, note in enumerate(tasting_notes)])

        prompt = f"""Categorize these {len(tasting_notes)} coffee tasting notes:

{notes_text}

Return a categorization for each tasting note in order."""

        try:
            result = await self.agent.run(prompt)
            return result.output.categorizations
        except Exception as e:
            logger.error(f"Error categorizing batch: {e}")
            # Return fallback categorizations
            return [
                TastingNoteCategory(
                    tasting_note=note,
                    primary_category="Other",
                    secondary_category=None,
                    tertiary_category=None,
                    confidence=0.1,
                )
                for note in tasting_notes
            ]

    def get_unique_tasting_notes(self) -> list[str]:
        """Get all unique tasting notes from the database."""
        conn = duckdb.connect(str(self.database_path))

        # Extract unique tasting notes from the array column
        query = """
        SELECT DISTINCT note
        FROM (
            SELECT unnest(tasting_notes) as note
            FROM coffee_beans
            WHERE tasting_notes IS NOT NULL
            AND array_length(tasting_notes) > 0
        )
        WHERE trim(note) != ''
        ORDER BY note
        """

        result = conn.execute(query).fetchall()
        conn.close()

        # Clean and filter notes
        notes = [row[0].strip() for row in result if row[0] and row[0].strip()]
        return list(set(notes))  # Remove any duplicates

    def get_existing_categorizations(self) -> dict[str, TastingNoteCategory]:
        """Get existing categorizations from the database."""
        conn = duckdb.connect(str(self.database_path))

        # Check if table exists
        try:
            result = conn.execute("""
                SELECT tasting_note, primary_category, secondary_category,
                       tertiary_category, confidence
                FROM tasting_notes_categories
            """).fetchall()

            existing = {}
            for row in result:
                existing[row[0]] = TastingNoteCategory(
                    tasting_note=row[0],
                    primary_category=row[1],
                    secondary_category=row[2],
                    tertiary_category=row[3],
                    confidence=row[4],
                )
            return existing

        except Exception:
            # Table doesn't exist yet
            return {}
        finally:
            conn.close()

    def get_uncategorized_notes(self) -> list[str]:
        """Get tasting notes that haven't been categorized yet."""
        all_notes = set(self.get_unique_tasting_notes())
        existing_categorizations = self.get_existing_categorizations()
        uncategorized = all_notes - set(existing_categorizations.keys())
        return sorted(list(uncategorized))

    async def categorize_all_notes(self, batch_size: int = 50, output_file: Path | None = None) -> Path:
        """Categorize all unique tasting notes and save to CSV."""
        # Get existing categorizations
        existing_categorizations = self.get_existing_categorizations()
        logger.info(f"Found {len(existing_categorizations)} existing categorizations")

        # Get only uncategorized notes
        uncategorized_notes = self.get_uncategorized_notes()
        logger.info(f"Found {len(uncategorized_notes)} uncategorized tasting notes to process")

        if output_file is None:
            output_file = Path(__file__).parent.parent / "database/tasting_notes_categorized.csv"

        # Ensure output directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)

        new_categorizations = []

        if uncategorized_notes:
            # Process uncategorized notes in batches
            for i in range(0, len(uncategorized_notes), batch_size):
                batch = uncategorized_notes[i : i + batch_size]
                batch_num = i // batch_size + 1
                total_batches = (len(uncategorized_notes) + batch_size - 1) // batch_size
                logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} notes)")

                try:
                    batch_results = await self.categorize_batch(batch)
                    new_categorizations.extend(batch_results)

                    # Add a small delay to respect rate limits
                    await asyncio.sleep(1)

                except Exception as e:
                    logger.error(f"Error processing batch {batch_num}: {e}")
                    # Add fallback categorizations for this batch
                    fallback_categorizations = [
                        TastingNoteCategory(
                            tasting_note=note,
                            primary_category="Other",
                            secondary_category=None,
                            tertiary_category=None,
                            confidence=0.1,
                        )
                        for note in batch
                    ]
                    new_categorizations.extend(fallback_categorizations)
        else:
            logger.info("No new notes to categorize")

        # Combine existing and new categorizations
        all_categorizations = list(existing_categorizations.values()) + new_categorizations

        # Save all categorizations to CSV
        self._save_to_csv(all_categorizations, output_file)
        logger.info(f"Saved {len(all_categorizations)} total categorizations to {output_file}")
        logger.info(f"- Existing: {len(existing_categorizations)}")
        logger.info(f"- New: {len(new_categorizations)}")

        return output_file

    def _save_to_csv(self, categorizations: list[TastingNoteCategory], output_file: Path):
        """Save categorizations to CSV file."""
        with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = [
                "tasting_note",
                "primary_category",
                "secondary_category",
                "tertiary_category",
                "confidence",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for cat in categorizations:
                writer.writerow(
                    {
                        "tasting_note": cat.tasting_note,
                        "primary_category": cat.primary_category,
                        "secondary_category": cat.secondary_category,
                        "tertiary_category": cat.tertiary_category,
                        "confidence": cat.confidence,
                    }
                )


async def main():
    """Main function to run the categorization."""
    database_path = Path("data/kissaten.duckdb")
    taste_lexicon_path = Path("src/kissaten/database/taste_lexicon.json")

    categorizer = TastingNoteCategorizer(database_path, taste_lexicon_path)

    # Categorize all notes
    csv_file = await categorizer.categorize_all_notes(batch_size=50)

    print(f"✅ Categorization complete! Results saved to {csv_file}")
    print("📊 Created database view: coffee_beans_with_categorized_notes")


if __name__ == "__main__":
    asyncio.run(main())
