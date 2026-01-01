"""
Varietal categorizer using pydantic-ai to clean and standardize coffee varietal names.

This script:
1. Uses coffee_varietals.json as a reference for canonical names
2. Splits compound varietal strings (e.g., "Caturra, Typica" -> ["Caturra", "Typica"])
3. Merges misspellings and case variations
4. Maintains mapping between original and cleaned names
"""

import json
from functools import lru_cache
from pathlib import Path

import dotenv
import duckdb
import logfire
import typer
from pydantic import BaseModel, Field, field_validator
from pydantic_ai import Agent
from rich.console import Console
from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.table import Table

# Typer CLI
app = typer.Typer()

logging = __import__("logging")
logger = logging.getLogger(__name__)
console = Console()

# Load environment variables from .env file
dotenv.load_dotenv()

logfire.configure(scrubbing=False)
logfire.instrument_pydantic_ai()


class VarietalMapping(BaseModel):
    """Model for mapping between original and canonical varietal names."""

    original_name: str = Field(description="The original varietal name from the dataset")
    canonical_names: list[str] = Field(
        description="List of canonical varietal names (can be multiple if the original contains multiple varieties)"
    )
    confidence: float = Field(default=1.0, description="Confidence score for this mapping (0-1)")
    is_compound: bool = Field(
        default=False, description="Whether this is a compound varietal string with multiple varieties"
    )
    separator: str | None = Field(
        default=None, description="The separator used if this is a compound varietal (e.g., ',', '&', '/')"
    )

    @field_validator("original_name")
    def clean_original_name(cls, v):
        """Keep original name exactly as is for mapping purposes."""
        return v.strip() if v else v

    @field_validator("canonical_names")
    def clean_canonical_names(cls, v):
        """Clean and normalize canonical names."""
        return [name.strip() for name in v if name and name.strip()]

    @field_validator("separator")
    def clean_separator(cls, v):
        """Clean and validate separator - should only contain punctuation/symbols."""
        if v is None:
            return v

        # Remove any alphanumeric characters, keeping only punctuation and whitespace
        import re

        cleaned = "".join(c for c in v if not c.isalnum())
        cleaned = cleaned.strip()

        # If nothing left, return None
        if not cleaned:
            return None

        return cleaned


class VarietalBatch(BaseModel):
    """Model for a batch of varietal mappings."""

    mappings: list[VarietalMapping] = Field(description="List of varietal mappings")
    batch_index: int = Field(default=0, description="Index of the current batch (0-based)")
    total_batches: int = Field(default=1, description="Total number of batches")


class ConflictResolution(BaseModel):
    """Model for resolving conflicts between different mappings."""

    original_names: list[str] = Field(description="List of original names that might map to the same canonical name")
    canonical_name: str = Field(description="The canonical name they should map to")
    should_merge: bool = Field(description="Whether these should actually be merged")
    reason: str = Field(description="Explanation for the merge decision")


class VarietalCategorizer:
    def __init__(self, database_path: Path, mappings_file: Path | None = None):
        self.database_path = database_path
        self.mappings_file = mappings_file or Path(__file__).parent.parent / "database/varietal_mappings.json"
        self.varietals_reference = self._load_varietals_reference()
        self.agent = self._create_agent()
        self.merge_agent = self._create_merge_agent()
        self.conflict_agent = self._create_conflict_resolution_agent()

    def _load_varietals_reference(self) -> dict[str, dict]:
        """Load the coffee varietals reference data from coffee_varietals.json."""
        varietals_file = Path(__file__).parent.parent / "database/coffee_varietals.json"

        if not varietals_file.exists():
            console.print(f"[yellow]Warning: {varietals_file} not found. Proceeding without reference data.[/yellow]")
            return {}

        with open(varietals_file) as f:
            varietals_data = json.load(f)

        # Create a lookup dictionary with normalized names
        lookup = {}
        for varietal in varietals_data:
            name = varietal.get("name", "")
            if name:
                # Store both original case and lowercase for matching
                lookup[name] = varietal
                lookup[name.lower()] = varietal

                # Also store alternate names if present
                if "alternate_names" in varietal:
                    for alt_name in varietal["alternate_names"]:
                        lookup[alt_name] = varietal
                        lookup[alt_name.lower()] = varietal

        console.print(f"[green]Loaded {len(varietals_data)} reference varietals from {varietals_file}[/green]")
        return lookup

    def _create_agent(self) -> Agent[None, VarietalBatch]:
        """Create the main categorization agent."""

        # Build a reference list of known varietals for the agent
        known_varietals = list(
            set(varietal.get("name", "") for varietal in self.varietals_reference.values() if "name" in varietal)
        )
        known_varietals_str = ", ".join(sorted(known_varietals)[:100])  # First 100 for context

        system_prompt = f"""You are a coffee varietal expert. Your task is to clean and standardize coffee varietal names.

REFERENCE VARIETALS (partial list): {known_varietals_str}

RULES:
1. Simple Varietals (Single):
   - Map to the canonical name from the reference list if it exists.
   - Standardize spelling (e.g., "Geisha" -> "Gesha", "Cattura" -> "Caturra").
   - Standardize translations (e.g., "Bourbon Rosado" -> "Pink Bourbon", "Yellow Catuai" -> "Catuai Amarillo" depending on reference).
   - Preserve specific hybrid names (e.g., "F1 Centroamericano", "Mundo Novo").

2. Field Blends & Generic Groups (CRITICAL):
   - Identify terms indicating a mix without specific varieties: "Field Blend", "Mixed", "Varios", "Variadades", "Local Landraces", "Garden Blend".
   - Map these to the canonical name "Field Blend" (or "Ethiopian Landrace" if specific to Ethiopia/Heirloom context).
   - Do NOT split these into components. Do NOT set is_compound=True unless it is mixed with a known variety (e.g., "Caturra & Field Blend").

3. Compound Varietals (Multiple Specific Varieties):
   - Identify when distinct, known varieties are listed together.
   - Split them into separate canonical names.
   - Set is_compound=True.
   - Extract ONLY the separator punctuation.
   - Examples:
     * "Caturra, Typica" -> ["Caturra", "Typica"], separator=", "
     * "Bourbon / Catuai" -> ["Bourbon", "Catuai"], separator=" / "
     * "Pink Bourbon + Field Blend" -> ["Pink Bourbon", "Field Blend"], separator=" + "

4. Ambiguous & Landrace Names:
   - "Ethiopian Heirloom", "Heirloom", "Native" -> Map to "Ethiopian Landrace" or "Heirloom" (be consistent).
   - "74110", "74112" -> Keep as distinct JARC varieties.
   - "SL28", "SL-28" -> Standardize format (usually "SL28").

5. Confidence Scoring:
   - 1.0: Exact reference match.
   - 0.9: Spelling fix or standard translation.
   - 0.8: Compound split or "Field Blend" categorization.
   - <0.7: Uncertain guess.

Return structured mappings with standardized canonical names."""

        return Agent(
            "gemini-3-flash-preview",
            system_prompt=system_prompt,
            output_type=VarietalBatch,
        )

    def _create_merge_agent(self) -> Agent[None, VarietalBatch]:
        """Create an agent for merging similar varietal names."""

        system_prompt = """You are reviewing varietal mappings to identify duplicates and variations that should be merged.

Your task is to find canonical names that are practically the same varietal:
1. Language variations: "Pink Bourbon" vs "Bourbon Rosado" (Prefer English/Standard form).
2. Spelling/Case: "Geisha" vs "Gesha", "Typica" vs "TYPICA".
3. Formatting: "SL 28" vs "SL-28" vs "SL28".
4. Generic Terms: "Heirloom" vs "Ethiopian Heirloom" vs "Indigenous Landrace" (Merge to most descriptive standard).
5. Blends: "Mixed" vs "Field Blend" vs "Varios" (Merge to "Field Blend").

DO NOT merge:
- Distinct Colors: "Red Bourbon" != "Yellow Bourbon".
- Distinct Codes: "74110" != "74112".
- Distinct Hybrids: "Castillo" != "V. Colombia".
- Compound vs Single: "Caturra, Typica" != "Caturra".

Return corrected mappings with the preferred canonical form."""

        return Agent(
            "gemini-3-flash-preview",
            system_prompt=system_prompt,
            output_type=VarietalBatch,
        )

    def _create_conflict_resolution_agent(self) -> Agent[None, ConflictResolution]:
        """Create an agent for resolving conflicts in mappings."""

        system_prompt = """You are a specialty coffee varietal expert resolving data mapping conflicts.

You have been given a 'Canonical Name' and a list of 'Original Names' that have been mapped to it.
Your goal: Verify if these Original Names are truly synonyms/variations of the Canonical Name.

APPROVE MERGE (should_merge = True) if:
1. Exact Synonyms/Translations: "Geisha" & "Gesha"; "Bourbon Rosado" & "Pink Bourbon".
2. Spelling/Formatting: "SL-28" & "SL 28"; "Cattura" & "Caturra".
3. Generic Blend Terms: "Mixed", "Varios", "Variadades", "Garden Blend" -> "Field Blend".
4. Landrace Synonyms: "Heirloom", "Native", "Local Landrace" -> "Ethiopian Landrace".

REJECT MERGE (should_merge = False) if:
1. Distinct Varieties: Mapped "Caturra" and "Castillo" to the same name.
2. Distinct Attributes: Mapped "Red Bourbon" and "Pink Bourbon" to the same name (Color matters).
3. Distinct Numeric Codes: Mapped "74110" and "74112" together (JARC varieties are distinct).
4. Hybrids vs Parents: Mapped "Pacamara" to "Pacas" (Distinct varietals).

If the grouping loses significant botanical information or conflates distinct varieties, reject it.
Provide a clear reason based on coffee botany."""

        return Agent(
            "gemini-3-flash-preview",
            system_prompt=system_prompt,
            output_type=ConflictResolution,
        )

    @lru_cache(maxsize=1)
    def load_existing_mappings(self) -> dict[str, VarietalMapping]:
        """Load existing mappings from the mappings file."""
        if not self.mappings_file.exists():
            return {}

        try:
            with open(self.mappings_file) as f:
                data = json.load(f)

            mappings = {}
            for item in data:
                mapping = VarietalMapping(**item)
                mappings[mapping.original_name] = mapping

            console.print(f"[green]Loaded {len(mappings)} existing mappings from {self.mappings_file}[/green]")
            return mappings
        except Exception as e:
            console.print(f"[red]Error loading existing mappings: {e}[/red]")
            return {}

    def save_mappings(self, mappings: list[VarietalMapping]) -> None:
        """Save mappings to the mappings file."""
        # Ensure directory exists
        self.mappings_file.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict for JSON serialization
        data = [mapping.model_dump() for mapping in mappings]

        with open(self.mappings_file, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        console.print(f"[green]Saved {len(mappings)} mappings to {self.mappings_file}[/green]")

    def get_unique_varietal_names(self) -> list[str]:
        """Get all unique varietal names from the database."""
        conn = duckdb.connect(str(self.database_path))

        query = """
        SELECT DISTINCT variety
        FROM origins
        WHERE variety IS NOT NULL AND variety != ''
        ORDER BY variety
        """

        result = conn.execute(query).fetchall()
        conn.close()

        varietals = [row[0] for row in result]
        console.print(f"[cyan]Found {len(varietals)} unique varietal names in database[/cyan]")
        return varietals

    def detect_conflicts(self, mappings: list[VarietalMapping]) -> dict[str, list[str]]:
        """Detect conflicts where multiple original names map to the same canonical name."""
        canonical_to_originals = {}

        for mapping in mappings:
            for canonical_name in mapping.canonical_names:
                if canonical_name not in canonical_to_originals:
                    canonical_to_originals[canonical_name] = []
                canonical_to_originals[canonical_name].append(mapping.original_name)

        # Find conflicts (where multiple originals map to same canonical)
        conflicts = {
            canonical: originals for canonical, originals in canonical_to_originals.items() if len(originals) > 1
        }

        if conflicts:
            console.print(f"[yellow]Found {len(conflicts)} potential conflicts[/yellow]")

        return conflicts

    async def resolve_conflicts(self, conflicts: dict[str, list[str]]) -> dict[str, list[str]]:
        """Use AI to resolve conflicts between mappings."""
        resolved = {}

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
        ) as progress:
            task = progress.add_task("[cyan]Resolving conflicts...", total=len(conflicts))

            for canonical_name, original_names in conflicts.items():
                try:
                    result = await self.conflict_agent.run(
                        f"Original names: {original_names}\nCanonical name: {canonical_name}\n\n"
                        f"Should these be merged? Explain your reasoning."
                    )

                    resolution = result.output
                    if resolution.should_merge:
                        resolved[canonical_name] = original_names
                        console.print(
                            f"[green]✓ Merging {len(original_names)} variants ({original_names}) to '{canonical_name}': {resolution.reason}[/green]"
                        )
                    else:
                        console.print(
                            f"[yellow]✗ Not merging variants for '{canonical_name}' -> {original_names}: {resolution.reason}[/yellow]"
                        )

                except Exception as e:
                    console.print(f"[red]Error resolving conflict for '{canonical_name}': {e}[/red]")

                progress.update(task, advance=1)

        return resolved

    async def categorize_varietals_batched(
        self, varietals: list[str], batch_size: int = 50, existing_mappings: dict[str, VarietalMapping] | None = None
    ) -> list[VarietalMapping]:
        """Categorize varietals in batches using AI."""
        if existing_mappings is None:
            existing_mappings = {}

        # Filter out varietals that already have mappings
        new_varietals = [v for v in varietals if v not in existing_mappings]

        if not new_varietals:
            console.print("[green]All varietals already have mappings![/green]")
            return list(existing_mappings.values())

        console.print(
            f"[cyan]Processing {len(new_varietals)} new varietals ({len(existing_mappings)} already mapped)[/cyan]"
        )

        all_mappings = list(existing_mappings.values())
        total_batches = (len(new_varietals) + batch_size - 1) // batch_size

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
        ) as progress:
            task = progress.add_task("[cyan]Categorizing varietals...", total=total_batches)

            for i in range(0, len(new_varietals), batch_size):
                batch = new_varietals[i : i + batch_size]
                batch_index = i // batch_size

                # Create context for the agent - use simple list without numbers
                varietal_list = "\n".join([f"- {v}" for v in batch])

                prompt = f"""Analyze and categorize these {len(batch)} coffee varietal names (batch {batch_index + 1}/{total_batches}):

{varietal_list}

Tasks:
1. Identify if the input is a single variety, a specific compound (list of varieties), or a generic "Field Blend".
2. If it is a generic term (e.g., "Varios", "Mixed", "Unknown"), map it to "Field Blend".
3. If it contains multiple specific varieties (e.g., "Caturra & Castillo"), split them and define the separator.
4. Standardize names (e.g., "Bourbon Rosado" -> "Pink Bourbon").
5. Return the cleaned canonical names and confidence scores.

IMPORTANT: The separator field must ONLY contain punctuation (like " & ", " + ", "/"), never letters.

Return structured mappings."""

                try:
                    result = await self.agent.run(prompt)
                    batch_mappings = result.output.mappings

                    all_mappings.extend(batch_mappings)

                    # Log some examples from this batch
                    for mapping in batch_mappings[:3]:  # Show first 3
                        compound_marker = " (compound)" if mapping.is_compound else ""
                        console.print(f"  '{mapping.original_name}' → {mapping.canonical_names}{compound_marker}")

                except Exception as e:
                    console.print(f"[red]Error processing batch {batch_index + 1}: {e}[/red]")
                    # Create fallback mappings for this batch
                    for varietal in batch:
                        all_mappings.append(
                            VarietalMapping(
                                original_name=varietal,
                                canonical_names=[varietal],  # Keep as-is
                                confidence=0.5,
                                is_compound=False,
                            )
                        )

                progress.update(task, advance=1)

        return all_mappings

    def print_statistics(self, mappings: list[VarietalMapping]) -> None:
        """Print statistics about the mappings."""
        total = len(mappings)
        compound_count = sum(1 for m in mappings if m.is_compound)
        simple_count = total - compound_count

        # Count unique canonical names
        all_canonical = set()
        for mapping in mappings:
            all_canonical.update(mapping.canonical_names)

        # Confidence distribution
        high_conf = sum(1 for m in mappings if m.confidence >= 0.9)
        med_conf = sum(1 for m in mappings if 0.7 <= m.confidence < 0.9)
        low_conf = sum(1 for m in mappings if m.confidence < 0.7)

        table = Table(title="Varietal Mapping Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")

        table.add_row("Total Original Names", str(total))
        table.add_row("Simple Varietals", str(simple_count))
        table.add_row("Compound Varietals", str(compound_count))
        table.add_row("Unique Canonical Names", str(len(all_canonical)))
        table.add_row("High Confidence (≥0.9)", str(high_conf))
        table.add_row("Medium Confidence (0.7-0.9)", str(med_conf))
        table.add_row("Low Confidence (<0.7)", str(low_conf))

        console.print(table)

        # Show some examples of compound mappings
        compound_examples = [m for m in mappings if m.is_compound][:10]
        if compound_examples:
            console.print("\n[bold]Example Compound Mappings:[/bold]")
            for mapping in compound_examples:
                console.print(
                    f"  '{mapping.original_name}' → {mapping.canonical_names} (separator: '{mapping.separator}')"
                )

    async def categorize_all_varietals(self) -> Path:
        """Main method to categorize all varietals."""
        console.print("[bold cyan]Starting Varietal Categorization[/bold cyan]\n")

        # Load existing mappings
        existing_mappings = self.load_existing_mappings()

        # Get unique varietal names from database
        varietals = self.get_unique_varietal_names()

        if not varietals:
            console.print("[yellow]No varietals found in database[/yellow]")
            return self.mappings_file

        # Categorize in batches
        mappings = await self.categorize_varietals_batched(
            varietals, batch_size=50, existing_mappings=existing_mappings
        )

        # Save mappings
        self.save_mappings(mappings)

        # Detect and resolve conflicts
        conflicts = self.detect_conflicts(mappings)
        if conflicts:
            console.print(f"\n[yellow]Resolving {len(conflicts)} conflicts...[/yellow]")
            await self.resolve_conflicts(conflicts)

        # Print statistics
        console.print()
        self.print_statistics(mappings)

        console.print(f"\n[bold green]✓ Categorization complete! Mappings saved to {self.mappings_file}[/bold green]")
        return self.mappings_file

    async def review_and_merge_canonical_names(self) -> None:
        """Review canonical names and merge similar ones."""
        console.print("[bold cyan]Reviewing Canonical Names for Merging[/bold cyan]\n")

        # Load existing mappings
        mappings = list(self.load_existing_mappings().values())

        if not mappings:
            console.print("[yellow]No mappings found to review[/yellow]")
            return

        # Get all unique canonical names
        all_canonical = set()
        for mapping in mappings:
            all_canonical.update(mapping.canonical_names)

        canonical_list = sorted(all_canonical)
        console.print(f"[cyan]Found {len(canonical_list)} unique canonical names[/cyan]")

        # Send to merge agent for review
        batch_size = 100
        merged_mappings = {}

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
        ) as progress:
            task = progress.add_task("[cyan]Reviewing canonical names...", total=len(canonical_list) // batch_size + 1)

            for i in range(0, len(canonical_list), batch_size):
                batch = canonical_list[i : i + batch_size]

                canonical_str = "\n".join([f"{idx + 1}. {name}" for idx, name in enumerate(batch)])

                prompt = f"""Review these canonical varietal names and identify any that should be merged:

{canonical_str}

Look for:
- Case variations (Typica vs TYPICA)
- Spelling variations (Cattura vs Caturra)
- Format variations (SL 28 vs SL-28 vs SL28)

Return corrected mappings where needed."""

                try:
                    result = await self.merge_agent.run(prompt)
                    batch_mappings = result.output.mappings

                    for mapping in batch_mappings:
                        if mapping.original_name != mapping.canonical_names[0]:
                            merged_mappings[mapping.original_name] = mapping.canonical_names[0]
                            console.print(f"  Merge: '{mapping.original_name}' → '{mapping.canonical_names[0]}'")

                except Exception as e:
                    console.print(f"[red]Error reviewing batch: {e}[/red]")

                progress.update(task, advance=1)

        # Apply merges
        if merged_mappings:
            console.print(f"\n[cyan]Applying {len(merged_mappings)} merges...[/cyan]")

            updated_mappings = []
            for mapping in mappings:
                new_canonical = [merged_mappings.get(name, name) for name in mapping.canonical_names]
                updated_mappings.append(
                    VarietalMapping(
                        original_name=mapping.original_name,
                        canonical_names=new_canonical,
                        confidence=mapping.confidence,
                        is_compound=mapping.is_compound,
                        separator=mapping.separator,
                    )
                )

            self.save_mappings(updated_mappings)
            console.print("[bold green]✓ Merging complete![/bold green]")
        else:
            console.print("[green]No merges needed - canonical names are already consistent[/green]")


# CLI entrypoint
@app.command()
def categorize(
    review_and_merge: bool = typer.Option(
        False, "--review-and-merge", help="Run the review and merge phase after categorization"
    ),
    database_path: Path = typer.Option(
        Path(__file__).parent.parent.parent.parent / "data/rw_kissaten.duckdb",
        "--database-path",
        help="Path to the DuckDB database file",
    ),
):
    """Categorize coffee varietals using AI."""
    import asyncio

    categorizer = VarietalCategorizer(database_path)

    # Run categorization
    asyncio.run(categorizer.categorize_all_varietals())

    # Optionally run review and merge
    if review_and_merge:
        asyncio.run(categorizer.review_and_merge_canonical_names())


@app.command()
def review(
    database_path: Path = typer.Option(
        Path(__file__).parent.parent.parent.parent / "data/rw_kissaten.duckdb",
        "--database-path",
        help="Path to the DuckDB database file",
    ),
):
    """Review and merge similar canonical names."""
    import asyncio

    categorizer = VarietalCategorizer(database_path)
    asyncio.run(categorizer.review_and_merge_canonical_names())


if __name__ == "__main__":
    app()
