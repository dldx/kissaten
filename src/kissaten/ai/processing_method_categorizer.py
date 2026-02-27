
import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from functools import lru_cache

import dotenv
import duckdb
import logfire
from pydantic import BaseModel, Field, field_validator
from pydantic_ai import Agent
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.console import Console
from rich.table import Table

# Typer CLI
import typer

app = typer.Typer()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
console = Console()

# Load environment variables from .env file
dotenv.load_dotenv()

logfire.configure(scrubbing=False)
logfire.instrument_pydantic_ai()


class ProcessingMethodMapping(BaseModel):
    """Model for mapping between original and common processing method names."""

    original_name: str = Field(
        description="The original processing method name from the dataset"
    )
    common_name: str = Field(
        description="The standardized common name for this processing method"
    )
    confidence: float = Field(
        default=1.0,
        description="Confidence score for this mapping (0-1)"
    )

    @field_validator("original_name", "common_name")
    def clean_names(cls, v):
        """Clean up names by stripping whitespace and fixing common issues."""
        if v:
            v = v.strip()
            # Remove trailing quotes or apostrophes
            while v and v[-1] in ["'", '"']:
                v = v[:-1]
        return v


class ProcessingMethodBatch(BaseModel):
    """Model for a batch of processing method mappings."""

    mappings: List[ProcessingMethodMapping] = Field(
        description="List of processing method mappings"
    )
    batch_index: int = Field(
        default=0,
        description="Index of the current batch (0-based)"
    )
    total_batches: int = Field(
        default=1,
        description="Total number of batches"
    )


class ConflictResolution(BaseModel):
    """Model for resolving conflicts between different mappings."""

    original_names: List[str] = Field(
        description="List of original names that map to the same common name"
    )
    common_name: str = Field(
        description="The common name they all map to"
    )
    should_merge: bool = Field(
        description="Whether these should actually be merged"
    )
    reason: str = Field(
        description="Explanation for the merge decision"
    )


class ProcessCategorizer:
    def __init__(self, database_path: Path, mappings_file: Optional[Path] = None):
        self.database_path = database_path
        self.mappings_file = mappings_file or Path(__file__).parent.parent / "database/processing_methods_mappings.json"
        self.agent = self._create_agent()
        self.merge_agent = self._create_merge_agent()
        self.conflict_agent = self._create_conflict_resolution_agent()

    def _create_agent(self) -> Agent[None, ProcessingMethodBatch]:
        """Create the main categorization agent."""
        system_prompt = """
        You are an expert in coffee processing methods with deep knowledge of coffee production.
        Your task is to map coffee processing method names to standardized common names.

        CRITICAL RULES:
        1. ONLY merge names that refer to the EXACT SAME process
        2. DO NOT merge different processes even if they're similar
        3. Consider these distinct categories that should NEVER be merged:
           - Natural/Dry vs Washed/Wet vs Honey/Pulped Natural vs Semi-washed
           - Different fermentation methods (aerobic vs anaerobic)
           - Different drying methods (sun-dried vs mechanical)
           - Different decaffeination methods (EA vs Swiss Water vs CO2)

        Examples of CORRECT merges:
        - "Natural" and "Natural Process" → "Natural"
        - "EA Decaf" and "Ethyl Acetate Decaffeinated" → "Ethyl Acetate Decaf"
        - "Honey" and "Pulped Natural" → "Honey"

        Examples of INCORRECT merges (keep separate):
        - "Natural" and "Semi-washed" (different processes)
        - "Washed" and "Fully Washed" → "Washed"
        - "Anaerobic Natural" and "Natural" (different fermentation)
        - "Black Honey" and "Red Honey" (different honey levels)
        - "Swiss Water Decaf" and "EA Decaf" (different decaf methods)

        When standardizing names:
        - Use the most descriptive common term
        - Fix capitalization and typos
        - Remove redundant words but keep important qualifiers
        - Preserve distinctions between processes
        """
        return Agent(
            "gemini-2.5-flash",
            output_type=ProcessingMethodBatch,
            system_prompt=system_prompt,
        )

    def _create_merge_agent(self) -> Agent[None, ProcessingMethodBatch]:
        """Create agent specifically for reviewing and merging common names."""
        system_prompt = """
        You are a coffee processing expert reviewing existing categorizations.
        Your task is to identify common names that should be merged because they refer to the same process.

        Be VERY conservative - only merge if you're certain they're the same process.

        Examples of valid merges:
        - "Natural" and "Natural Process" → "Natural"
        - "EA Decaf" and "Ethyl Acetate Decaffeinated" → "Ethyl Acetate Decaf"
        - "Pulped Natural" and "Honey Process" → "Honey"

        Examples to keep separate:
        - "Fully Washed" and "Washed" → "Washed"
        - "Natural Anaerobic" and "Natural" (different fermentation)
        - "Yellow Honey" and "Red Honey" (different removal percentages)
        """
        return Agent(
            "gemini-2.5-flash",
            output_type=ProcessingMethodBatch,
            system_prompt=system_prompt,
        )

    def _create_conflict_resolution_agent(self) -> Agent[None, ConflictResolution]:
        """Create agent for resolving mapping conflicts."""
        system_prompt = """
        You are a coffee processing expert resolving conflicts in processing method mappings.
        When multiple original names map to the same common name, determine if they truly
        represent the same process or if they should be kept separate.

        Be conservative - if there's any doubt that they're different processes, keep them separate.
        """
        return Agent(
            "gemini-2.5-flash",
            output_type=ConflictResolution,
            system_prompt=system_prompt,
        )

    @lru_cache(maxsize=1)
    def load_mappings(self) -> Dict[str, ProcessingMethodMapping]:
        """Load existing mappings from JSON file with caching."""
        if not self.mappings_file.exists():
            logger.info(f"No existing mappings file at {self.mappings_file}")
            return {}

        try:
            with open(self.mappings_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            mappings = {}
            for item in data:
                mapping = ProcessingMethodMapping(**item)
                mappings[mapping.original_name] = mapping

            logger.info(f"Loaded {len(mappings)} existing mappings")
            return mappings
        except Exception as e:
            logger.error(f"Error loading mappings: {e}")
            return {}

    def save_mappings(self, mappings: List[ProcessingMethodMapping]) -> None:
        """Save mappings to JSON file."""
        self.mappings_file.parent.mkdir(parents=True, exist_ok=True)

        mappings_dict = [mapping.model_dump() for mapping in mappings]

        with open(self.mappings_file, "w", encoding="utf-8") as f:
            json.dump(mappings_dict, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved {len(mappings)} mappings to {self.mappings_file}")

    def get_unique_process_names(self) -> List[str]:
        """Get unique processing method names from database."""
        conn = duckdb.connect(str(self.database_path))
        query = """
        SELECT DISTINCT process
        FROM origins
        WHERE process IS NOT NULL AND trim(process) != ''
        ORDER BY process
        """
        result = conn.execute(query).fetchall()
        conn.close()
        return [row[0].strip() for row in result if row[0] and row[0].strip()]

    def detect_conflicts(self, mappings: List[ProcessingMethodMapping]) -> Dict[str, List[str]]:
        """Detect potential conflicts in mappings."""
        common_to_originals = {}

        for mapping in mappings:
            if mapping.common_name not in common_to_originals:
                common_to_originals[mapping.common_name] = []
            common_to_originals[mapping.common_name].append(mapping.original_name)

        # Find common names with multiple originals (potential over-merging)
        conflicts = {
            common: originals
            for common, originals in common_to_originals.items()
            if len(originals) > 1
        }

        return conflicts

    async def resolve_conflicts(self, conflicts: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Use AI to resolve potential conflicts."""
        resolved = {}

        for common_name, original_names in conflicts.items():
            if len(original_names) <= 1:
                continue

            prompt = f"""
            The following processing methods are all mapped to "{common_name}":
            {', '.join([f'"{name}"' for name in original_names])}

            Should these all be merged into the same common name, or should some be kept separate?
            Consider if they truly represent the same coffee processing method.
            """

            try:
                result = await self.conflict_agent.run(prompt)
                resolution = result.output

                if not resolution.should_merge:
                    logger.warning(
                        f"Conflict detected for '{common_name}': {resolution.reason}"
                    )
                    # Keep track of conflicts that shouldn't be merged
                    resolved[common_name] = original_names

            except Exception as e:
                logger.error(f"Error resolving conflict for {common_name}: {e}")

        return resolved

    async def categorize_methods_batched(
        self,
        methods: List[str],
        batch_size: int = 50,
        existing_mappings: Optional[Dict[str, ProcessingMethodMapping]] = None
    ) -> List[ProcessingMethodMapping]:
        """Process methods in batches with progress tracking."""

        if not methods:
            return []

        all_mappings = []
        existing_mappings = existing_mappings or {}

        # Get existing common names for context
        existing_common_names = set(m.common_name for m in existing_mappings.values())

        total_batches = (len(methods) + batch_size - 1) // batch_size

        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            transient=True,
        ) as progress:
            task = progress.add_task("Categorizing processing methods", total=total_batches)

            for batch_idx in range(total_batches):
                start_idx = batch_idx * batch_size
                end_idx = min(start_idx + batch_size, len(methods))
                batch = methods[start_idx:end_idx]

                prompt = f"""
                Categorize these {len(batch)} coffee processing methods.
                Map each to a standardized common name.

                Methods to categorize:
                {chr(10).join([f'{i+1}. "{name}"' for i, name in enumerate(batch)])}

                Existing common names to consider (use these when appropriate):
                {', '.join(sorted(existing_common_names)) if existing_common_names else 'None yet'}

                Remember: Only merge methods that are truly the same process.
                Keep different processes separate even if similar.
                """

                try:
                    result = await self.agent.run(prompt)
                    batch_mappings = result.output.mappings

                    # Validate mappings
                    validated_mappings = []
                    for mapping in batch_mappings:
                        # Ensure original name is from our batch
                        if mapping.original_name in batch:
                            validated_mappings.append(mapping)
                            existing_common_names.add(mapping.common_name)
                        else:
                            logger.warning(f"Skipping hallucinated mapping: {mapping.original_name}")

                    all_mappings.extend(validated_mappings)

                except Exception as e:
                    logger.error(f"Error processing batch {batch_idx + 1}: {e}")
                    # Fallback: map to original names
                    for name in batch:
                        all_mappings.append(ProcessingMethodMapping(
                            original_name=name,
                            common_name=name,
                            confidence=0.5
                        ))

                progress.update(task, advance=1)
                await asyncio.sleep(0.5)  # Rate limiting

        return all_mappings

    def print_statistics(self, mappings: List[ProcessingMethodMapping]) -> None:
        """Print statistics about the mappings."""
        common_counts = {}
        for mapping in mappings:
            common_counts[mapping.common_name] = common_counts.get(mapping.common_name, 0) + 1

        # Create table for statistics
        table = Table(title="Processing Method Categorization Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total Original Methods", str(len(mappings)))
        table.add_row("Unique Common Names", str(len(common_counts)))
        table.add_row("Average Methods per Common Name", f"{len(mappings) / len(common_counts):.2f}")

        console.print(table)

        # Show top merged categories
        if len(common_counts) > 0:
            sorted_counts = sorted(common_counts.items(), key=lambda x: x[1], reverse=True)[:10]

            merge_table = Table(title="Top 10 Merged Categories")
            merge_table.add_column("Common Name", style="cyan")
            merge_table.add_column("Count", style="green")

            for name, count in sorted_counts:
                if count > 1:  # Only show actual merges
                    merge_table.add_row(name, str(count))

            console.print(merge_table)

    async def categorize_all_methods(self) -> Path:
        """Main method to categorize all processing methods."""

        # Load existing mappings
        existing_mappings = self.load_mappings()

        # Get all unique method names from database
        all_methods = self.get_unique_process_names()
        logger.info(f"Found {len(all_methods)} unique processing methods in database")

        # Filter out already categorized methods
        methods_to_process = [
            m for m in all_methods
            if m not in existing_mappings
        ]

        if not methods_to_process:
            logger.info("All methods already categorized")
            self.print_statistics(list(existing_mappings.values()))
            return self.mappings_file

        logger.info(f"Processing {len(methods_to_process)} new methods")

        # Categorize new methods
        new_mappings = await self.categorize_methods_batched(
            methods_to_process,
            batch_size=50,
            existing_mappings=existing_mappings
        )

        # Combine with existing mappings
        all_mappings = list(existing_mappings.values()) + new_mappings

        # Detect and resolve conflicts
        conflicts = self.detect_conflicts(all_mappings)
        if conflicts:
            logger.info(f"Detected {len(conflicts)} potential conflicts")
            unresolved = await self.resolve_conflicts(conflicts)

            if unresolved:
                console.print(f"[yellow]Warning: {len(unresolved)} conflicts require manual review[/yellow]")
                for common, originals in list(unresolved.items())[:5]:
                    console.print(f"  '{common}': {originals[:3]}...")

        # Save mappings
        self.save_mappings(all_mappings)

        # Print statistics
        self.print_statistics(all_mappings)

        return self.mappings_file

    async def review_and_merge_common_names(self) -> None:
        """Review existing common names and suggest additional merges."""
        mappings = list(self.load_mappings().values())

        if not mappings:
            logger.info("No mappings to review")
            return

        # Get unique common names
        common_names = sorted(set(m.common_name for m in mappings))

        console.print(f"[cyan]Reviewing {len(common_names)} common names for potential merges...[/cyan]")

        # Process in batches
        batch_size = 20
        merge_suggestions = {}

        for i in range(0, len(common_names), batch_size):
            batch = common_names[i:i+batch_size]

            prompt = f"""
            Review these coffee processing method names and identify which should be merged:
            {chr(10).join([f'- "{name}"' for name in batch])}

            Only suggest merges for names that clearly refer to the SAME process.
            Be conservative - when in doubt, keep them separate.

            Return mappings where original_name is the current name and common_name is what it should be merged to.
            """

            try:
                result = await self.merge_agent.run(prompt)
                for mapping in result.output.mappings:
                    if mapping.original_name != mapping.common_name:
                        merge_suggestions[mapping.original_name] = mapping.common_name

            except Exception as e:
                logger.error(f"Error reviewing batch: {e}")

        if merge_suggestions:
            console.print(f"[green]Found {len(merge_suggestions)} potential merges[/green]")

            # Apply merges
            for mapping in mappings:
                if mapping.common_name in merge_suggestions:
                    mapping.common_name = merge_suggestions[mapping.common_name]

            # Save updated mappings
            self.save_mappings(mappings)
            console.print("[green]✅ Merges applied and saved[/green]")
        else:
            console.print("[yellow]No additional merges suggested[/yellow]")

# CLI entrypoint
@app.command()
def categorize(
    review_and_merge: bool = typer.Option(
        False,
        "--review-and-merge",
        help="Run the review and merge phase after categorization"
    ),
    database_path: Path = typer.Option(
        Path(__file__).parent.parent.parent.parent / "data/kissaten.duckdb",
        "--database-path",
        help="Path to the DuckDB database file"
    ),
):
    """Categorize coffee processing methods, optionally review and merge common names."""
    async def run():
        categorizer = ProcessCategorizer(database_path)
        console.print("[bold cyan]Starting coffee processing method categorization...[/bold cyan]")
        output_file = await categorizer.categorize_all_methods()
        console.print(f"[green]✅ Categorization complete! Results saved to {output_file}[/green]")
        if review_and_merge:
            console.print("\n[bold cyan]Reviewing common names for additional merges...[/bold cyan]")
            await categorizer.review_and_merge_common_names()
            console.print("[green]🔄 Review complete![/green]")
    asyncio.run(run())


if __name__ == "__main__":
    app()