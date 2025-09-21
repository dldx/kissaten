"""
Tasting note categorization using Gemini Flash 2.5 and PydanticAI.
This script can also update the taste lexicon with new tertiary categories.

Usage:
  - Default (categorize only new notes):
    python your_script_name.py

  - Update mode (re-categorize notes missing a tertiary category):
    python your_script_name.py --update-tertiary
"""

import argparse
import asyncio
import collections
import csv
import json
import logging
from datetime import datetime
from pathlib import Path

import dotenv
import duckdb
import logfire
from pydantic import BaseModel, Field, model_validator
from pydantic_ai import Agent

# Load environment variables from .env file
dotenv.load_dotenv()

logfire.configure(scrubbing=False)  # Initialize logfire for logging
logfire.instrument_pydantic_ai()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class TastingNoteCategory(BaseModel):
    """A tasting note categorization."""

    tasting_note: str
    primary_category: str
    secondary_category: str | None
    tertiary_category: str | None
    confidence: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_category_hierarchy(self) -> "TastingNoteCategory":
        """Ensure that a tertiary category is only present if a secondary is."""
        if self.tertiary_category and not self.secondary_category:
            raise ValueError(
                f"Tasting note '{self.tasting_note}' has a tertiary category "
                f"('{self.tertiary_category}') but no secondary category. This is not allowed."
            )
        return self


class TastingNoteBatch(BaseModel):
    """Batch of categorized tasting notes."""

    categorizations: list[TastingNoteCategory] = Field(description="List of categorized tasting notes")


# -- Models for Lexicon Update --
class CanonicalName(BaseModel):
    """The canonical name for a single flavor."""

    original_note: str
    canonical_name: str | None = Field(
        description="The single, specific, canonical flavor word, or null if not applicable."
    )


class CanonicalNameBatch(BaseModel):
    """A batch of canonical names for flavors."""

    names: list[CanonicalName]


class TastingNoteCategorizer:
    """Categorizes tasting notes and suggests lexicon updates using Gemini."""

    def __init__(self, database_path: Path, taste_lexicon_path: Path, categorized_csv_path: Path):
        self.database_path = database_path
        self.taste_lexicon_path = taste_lexicon_path
        self.categorized_csv_path = categorized_csv_path
        self.taste_lexicon_data = self._load_lexicon_data()
        self.taste_lexicon_str = json.dumps(self.taste_lexicon_data, indent=2)
        self.categorization_agent = self._create_categorization_agent()
        self.naming_agent = self._create_naming_agent()

    def _load_lexicon_data(self) -> dict:
        """Load the taste lexicon from JSON file as a dictionary."""
        if not self.taste_lexicon_path.exists():
            logger.warning(f"Lexicon file not found at {self.taste_lexicon_path}. Starting with an empty lexicon.")
            return {"categories": []}
        with open(self.taste_lexicon_path) as f:
            # Handle both formats (with and without _meta)
            data = json.load(f)
            return data.get("taste_lexicon", data)

    def _create_categorization_agent(self) -> Agent[None, TastingNoteBatch]:
        """Create the PydanticAI agent for categorization."""
        system_prompt = self._build_system_prompt()
        return Agent("gemini-2.5-flash", output_type=TastingNoteBatch, system_prompt=system_prompt)

    def _create_naming_agent(self) -> Agent[None, CanonicalNameBatch]:
        """Create a dedicated agent for extracting specific, non-redundant flavor names."""
        system_prompt = (
            "You are an expert linguist specializing in flavor terminology. You will be given a list of tasting notes "
            "along with their parent secondary category. Your task is to extract a single, canonical flavor word that "
            "is **more specific** than the parent category."
            "\n\nCRITICAL RULE: Return `null` for the canonical name if the tasting note is simply a synonym, plural, "
            "or general description of the parent secondary category. The goal is to find new, specific tertiary flavors, "
            "not to repeat the parent category."
            "\n\nEXAMPLES (Parent Secondary Category: 'Berry'):"
            "\n- 'Ripe Strawberry' -> 'Strawberry' (More specific)"
            "\n- 'Blueberries' -> 'Blueberry' (More specific, normalized)"
            "\n- 'Wild Berries' -> null (Not more specific than 'Berry')"
            "\n- 'A berry flavor' -> null (Synonym of 'Berry')"
            "\n\nEXAMPLES (Parent Secondary Category: 'Citrus Fruit'):"
            "\n- 'Bergamota' -> 'Bergamot' (Specific, translated)"
            "\n- 'Zest of lemon' -> 'Lemon' (Specific)"
            "\n- 'Citrusy notes' -> null (Synonym of 'Citrus Fruit')"
            "\n\nEXAMPLES (Parent Secondary Category: 'Fruity'):"
            "\n- 'Tropical Fruit Punch' -> 'Tropical Fruit' (Specific)"
            "\n- 'Just fruity' -> null (Not more specific)"
            "\n- 'Lots of fruit' -> null (Not more specific)"
        )
        return Agent("gemini-2.5-flash", output_type=CanonicalNameBatch, system_prompt=system_prompt)

    def _build_system_prompt(self) -> str:
        """Build the system prompt with the taste lexicon."""
        return (
            "You are an expert coffee taster and flavor categorization specialist. "
            "Your task is to categorize coffee tasting notes according to a standardized taste lexicon.\n\n"
            f"TASTE LEXICON CATEGORIES:\n{self.taste_lexicon_str}\n\n"
            "INSTRUCTIONS:\n"
            "1. For each tasting note, assign it to the most appropriate primary category.\n"
            "2. If applicable, also assign a secondary category.\n"
            "3. The `tertiary_category` should be used for more specific flavors. If a note like 'Strawberry Jam' matches a secondary category like 'Berry', the tertiary category should be the specific flavor, 'Strawberry', which is found in the lexicon's `flavors` list.\n"
            "4. **Maintain a strict hierarchy: a tertiary category REQUIRES a secondary category, and a secondary category REQUIRES a primary category.**\n"
            "5. Provide a confidence score (0.0-1.0) for your categorization.\n"
            '6. Handle variations and synonyms (e.g., "choc" = "chocolate", "Fresa" = "Strawberry").\n'
            '7. For compound notes (e.g., "dark chocolate"), identify the most specific category.\n'
            "8. If a note is a general term like 'berry' and not a specific one like 'strawberry', the tertiary category must be null.\n"
            "9. If a note doesn't clearly fit any category, use the closest match and lower confidence.\n\n"
            "HIERARCHY EXAMPLES:\n"
            '- "chocolate" → Primary: "Cocoa", Secondary: null, Tertiary: null, Confidence: 0.95\n'
            '- "berry" → Primary: "Fruity", Secondary: "Berry", Tertiary: null, Confidence: 0.90\n'
            '- "Strawberry Jam" → Primary: "Fruity", Secondary: "Berry", Tertiary: "Strawberry", Confidence: 0.95\n'
            '- "Lemon Zest" → Primary: "Fruity", Secondary: "Citrus Fruit", Tertiary: "Lemon", Confidence: 0.95\n'
            '- "funky" → Primary: "Alcohol/Fermented", Secondary: null, Tertiary: null, Confidence: 0.60\n\n'
            "Be consistent and precise in your categorizations. Focus on the dominant flavor characteristic."
        )

    async def categorize_batch(self, tasting_notes: list[str]) -> list[TastingNoteCategory]:
        """Categorize a batch of tasting notes."""
        notes_text = "\n".join(tasting_notes)
        prompt = f"Categorize these {len(tasting_notes)} coffee tasting notes:\n\n{notes_text}\n\nReturn a categorization for each tasting note in order."
        try:
            result = await self.categorization_agent.run(prompt)
            return result.output.categorizations
        except Exception as e:
            logger.error(f"Error categorizing batch (likely a validation error): {e}")
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

    async def get_canonical_names_batch(self, tasting_notes: list[str], secondary_category: str) -> list[str | None]:
        """Get canonical names for a batch of tasting notes, providing context of the parent category."""
        notes_text = "\n".join(tasting_notes)
        prompt = f"""The parent secondary category is: '{secondary_category}'.

Extract the canonical flavor name for each of these {len(tasting_notes)} notes:

{notes_text}"""
        try:
            result = await self.naming_agent.run(prompt)
            name_map = {item.original_note: item.canonical_name for item in result.output.names}
            return [name_map.get(note) for note in tasting_notes]
        except Exception as e:
            logger.error(f"Error getting canonical names: {e}")
            return [None for _ in tasting_notes]

    async def update_lexicon_with_new_tertiary_categories(
        self, min_count: int = 3, batch_size: int = 50, output_lexicon_path: Path | None = None
    ):
        """Analyzes categorized notes to find and add new tertiary categories to the lexicon."""
        logger.info("Starting lexicon update process...")

        if not self.categorized_csv_path.exists():
            logger.error(f"Categorized notes file not found at {self.categorized_csv_path}")
            return

        conn = duckdb.connect()
        query = f"""
            SELECT primary_category, secondary_category, tasting_note
            FROM read_csv_auto('{self.categorized_csv_path}')
            WHERE tertiary_category IS NULL AND secondary_category IS NOT NULL
        """
        results = conn.execute(query).fetchall()
        conn.close()

        if not results:
            logger.info("No notes found that are candidates for new tertiary categories.")
            return

        grouped_notes = collections.defaultdict(list)
        for primary, secondary, note in results:
            grouped_notes[(primary, secondary)].append(note)

        new_additions = collections.defaultdict(list)

        for (primary, secondary), notes in grouped_notes.items():
            logger.info(f"Analyzing {len(notes)} notes for {primary} -> {secondary}...")
            canonical_names = []
            for i in range(0, len(notes), batch_size):
                batch = notes[i : i + batch_size]
                names = await self.get_canonical_names_batch(batch, secondary_category=secondary)
                canonical_names.extend(names)
                await asyncio.sleep(1)

            valid_names = [name.strip().title() for name in canonical_names if name and name.strip()]
            if not valid_names:
                continue

            counts = collections.Counter(valid_names)

            lexicon_entry = next(
                (
                    cat
                    for cat in self.taste_lexicon_data["categories"]
                    if cat["primary_category"] == primary and cat["secondary_category"] == secondary
                ),
                None,
            )
            existing_flavors = {f.lower() for f in lexicon_entry["flavors"]} if lexicon_entry else set()

            for name, count in counts.items():
                if count >= min_count and name.lower() not in existing_flavors:
                    logger.info(
                        f"  -> Found new potential category: '{name}' (count: {count}) under {primary} -> {secondary}"
                    )
                    new_additions[(primary, secondary)].append(name)

        if not new_additions:
            logger.info("No new tertiary categories met the threshold for addition.")
            return

        for (primary, secondary), new_flavors in new_additions.items():
            for category in self.taste_lexicon_data["categories"]:
                if category["primary_category"] == primary and category["secondary_category"] == secondary:
                    category["flavors"].extend(new_flavors)
                    category["flavors"].sort()
                    break

        self._save_lexicon(output_lexicon_path)

    def _save_lexicon(self, output_path: Path | None):
        if output_path is None:
            output_path = self.taste_lexicon_path
        header = {
            "comment": "This lexicon has been automatically updated with AI-generated tertiary categories.",
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "warning": "These additions are not official and should be reviewed.",
        }
        output_data = {"_meta": header, "categories": self.taste_lexicon_data["categories"]}
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2)
        logger.info(f"✅ Lexicon updated successfully. Saved to {output_path}")

    def get_unique_tasting_notes_from_db(self) -> list[str]:
        conn = duckdb.connect(str(self.database_path))
        query = "SELECT DISTINCT unnest(tasting_notes) as note FROM coffee_beans WHERE tasting_notes IS NOT NULL AND array_length(tasting_notes) > 0 ORDER BY note"
        result = conn.execute(query).fetchall()
        conn.close()
        return [row[0].strip() for row in result if row[0] and row[0].strip()]

    def get_existing_categorizations(self) -> dict[str, TastingNoteCategory]:
        if not self.categorized_csv_path.exists():
            return {}
        existing = {}
        with open(self.categorized_csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                secondary = row.get("secondary_category") or None
                tertiary = row.get("tertiary_category") or None
                existing[row["tasting_note"]] = TastingNoteCategory(
                    tasting_note=row["tasting_note"],
                    primary_category=row["primary_category"],
                    secondary_category=secondary if secondary else None,
                    tertiary_category=tertiary if tertiary else None,
                    confidence=float(row["confidence"]),
                )
        return existing

    def get_notes_to_process(self, update_tertiary: bool) -> list[str]:
        """Determines which notes need to be categorized based on the mode."""
        all_db_notes = set(self.get_unique_tasting_notes_from_db())
        existing_categorizations = self.get_existing_categorizations()

        # Always process notes that are in the DB but not yet in our CSV
        new_notes = all_db_notes - set(existing_categorizations.keys())

        if not update_tertiary:
            logger.info(f"Default mode: processing {len(new_notes)} new notes.")
            return sorted(list(new_notes))
        else:
            # In update mode, also find existing notes that lack a tertiary category
            notes_to_update = {
                note
                for note, cat in existing_categorizations.items()
                if cat.tertiary_category is None and cat.secondary_category is not None
            }
            notes_to_process = new_notes.union(notes_to_update)
            logger.info(
                f"Update mode: processing {len(new_notes)} new notes and "
                f"{len(notes_to_update)} existing notes needing tertiary update."
            )
            return sorted(list(notes_to_process))

    async def categorize_all_notes(self, batch_size: int = 50, update_tertiary: bool = False):
        """Categorize all unique tasting notes and save to CSV."""
        existing_categorizations = self.get_existing_categorizations()
        logger.info(f"Found {len(existing_categorizations)} existing categorizations.")

        notes_to_process = self.get_notes_to_process(update_tertiary)
        logger.info(f"Found {len(notes_to_process)} total notes to process.")

        self.categorized_csv_path.parent.mkdir(parents=True, exist_ok=True)

        if notes_to_process:
            for i in range(0, len(notes_to_process), batch_size):
                batch = notes_to_process[i : i + batch_size]
                batch_num = i // batch_size + 1
                total_batches = (len(notes_to_process) + batch_size - 1) // batch_size
                logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} notes)")
                try:
                    batch_results = await self.categorize_batch(batch)
                    # Check if each tasting note is present in the database first
                    batch_results = [cat for cat in batch_results if cat.tasting_note in notes_to_process]
                    # Update the main dictionary with new/updated results
                    for cat in batch_results:
                        existing_categorizations[cat.tasting_note] = cat
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"Error processing batch {batch_num}: {e}")
        else:
            logger.info("No new or updatable notes to process.")

        all_categorizations = sorted(list(existing_categorizations.values()), key=lambda x: x.tasting_note)
        self._save_to_csv(all_categorizations)
        logger.info(f"Saved {len(all_categorizations)} total categorizations to {self.categorized_csv_path}")

    def _save_to_csv(self, categorizations: list[TastingNoteCategory]):
        """Save categorizations to CSV file."""
        with open(self.categorized_csv_path, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = ["tasting_note", "primary_category", "secondary_category", "tertiary_category", "confidence"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for cat in categorizations:
                writer.writerow(cat.model_dump())


async def main():
    """Main function to run the categorization and lexicon update."""
    parser = argparse.ArgumentParser(description="Categorize coffee tasting notes and update taste lexicon.")
    parser.add_argument(
        "--update-missing",
        action="store_true",
        help="Re-categorize existing notes that are missing a tertiary category.",
    )
    args = parser.parse_args()

    # Define file paths
    database_path = Path("data/kissaten.duckdb")
    categorized_csv_path = Path(__file__).parent.parent / "database/tasting_notes_categorized.csv"
    taste_lexicon_path = Path(__file__).parent.parent / "database/taste_lexicon.json"

    # Initialize the categorizer
    categorizer = TastingNoteCategorizer(database_path, taste_lexicon_path, categorized_csv_path)

    # Step 1: Categorize notes. The mode is controlled by the CLI flag.
    await categorizer.categorize_all_notes(batch_size=50, update_tertiary=args.update_missing)
    print(f"✅ Categorization complete! Results saved to {categorized_csv_path}")

    # Step 2: Use the (now updated) categorization results to suggest lexicon updates.
    await categorizer.update_lexicon_with_new_tertiary_categories(
        min_count=3,
        output_lexicon_path=taste_lexicon_path,
    )


if __name__ == "__main__":
    asyncio.run(main())