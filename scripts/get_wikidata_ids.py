import asyncio
import json
import logging
import os
import time
from typing import Literal

import polars as pl
import requests
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.table import Table

load_dotenv()

# Setup Rich console and logging
console = Console()
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, rich_tracebacks=True)],
)
logger = logging.getLogger(__name__)

class FlavorEntity(BaseModel):
    flavor_note: str
    source: Literal["wikidata", "manual"]
    label: str
    description: str
    id: str
    image_url: str
    image_author: str | None
    image_license: str | None
    image_license_url: str | None


class WikidataEntityCandidate(BaseModel):
    """A candidate Wikidata entity for selection."""
    id: str
    label: str
    description: str


class EntitySelectionResponse(BaseModel):
    """Response from the AI agent for entity selection."""
    reasoning: str = Field(description="Brief explanation of why this entity was selected")
    selected_entity_id: str | None = Field(
        description="The ID of the most relevant Wikidata entity. None if no entity was selected."
    )


# Initialize the Gemini Flash Lite agent for entity selection
entity_selector_agent = Agent(
    model="gemini-2.5-flash-lite",
    output_type=EntitySelectionResponse,
    system_prompt="""You are an expert at selecting the most relevant Wikidata entity for coffee flavor notes.

Given a flavor note (like "chocolate", "citrus", "floral") and a list of candidate Wikidata entities,
select the entity that is most relevant to coffee tasting and flavor description.

Guidelines:
1. Prioritize entities that are directly related to food, flavors, or sensory experiences
2. Avoid overly specific entities unless they're clearly the best match
3. For fruit flavors, prefer the fruit itself over specific varieties unless specified
4. For general categories (like "floral"), prefer the broader concept over specific flowers
5. Consider the context of coffee tasting and flavor profiling
6. Occasionally, you will get entities that have the same name as the flavour but are otherwise unrelated to the concept of the flavour. In this case, you should ignore them.
7. Paintings of a flavour can be relevant, but only if they are clearly related to the flavour.

If all candidates are irrelevant, return None.

Be concise in your reasoning (1-2 sentences max)."""
)


async def select_best_entity(flavor_note: str, candidates: list[WikidataEntityCandidate]) -> str | None:
    """
    Use AI agent to select the best Wikidata entity from candidates.

    Args:
        flavor_note: The flavor note being searched for
        candidates: List of candidate entities

    Returns:
        The ID of the selected entity, or None if selection fails
    """
    if not candidates:
        return None

    if len(candidates) == 1:
        return candidates[0].id

    try:
        # Prepare the prompt with candidate information
        candidates_text = "\n".join([
            f"{c}"
            for c in candidates
        ])
        print(candidates_text)

        prompt = f"""Flavor note: "{flavor_note}"

Available Wikidata entities:
{candidates_text}

Select the most relevant entity for this coffee flavor note."""

        logger.debug(f"Asking AI agent to select entity for '{flavor_note}' from {len(candidates)} candidates")
        result = await entity_selector_agent.run(prompt)

        # Validate that the selected ID exists in candidates
        candidate_ids = {c.id for c in candidates}
        if result.output.selected_entity_id in candidate_ids:
            logger.info(
                f"AI selected entity {result.output.selected_entity_id} for '{flavor_note}': {result.output.reasoning}"
            )
            return result.output.selected_entity_id
        else:
            logger.warning(
                f"AI selected invalid entity ID {result.output.selected_entity_id} or no entity was selected"
            )
            return None

    except Exception as e:
        logger.warning(f"AI entity selection failed for '{flavor_note}': {e}")
        return None


async def find_wikidata_flavor_entity_async(flavor_note: str) -> FlavorEntity | None:
    """
    Finds the best Wikidata entity for a flavor using AI selection.

    Args:
        flavor_note (str): A flavor note for a single flavor

    Returns:
        FlavorEntity or None: A FlavorEntity containing 'label', 'description', 'id', and 'image_url'
                      of the best matching Wikidata entity, or None if no suitable entity
                      with an image is found.
    """
    wikidata_api_url = "https://www.wikidata.org/w/api.php"
    logger.debug(f"Searching Wikidata for flavor note: '{flavor_note}'")

    params = {
        "action": "wbsearchentities",
        "format": "json",
        "language": "en",
        "search": flavor_note,
        "type": "item",
        "limit": 10,  # Increased limit for better AI selection
    }
    headers = {"User-Agent": "Kissaten/1.0 (https://github.com/dldx/kissaten)"}

    try:
        response = requests.get(wikidata_api_url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if "search" in data and data["search"]:
            logger.debug(f"Found {len(data['search'])} search results for '{flavor_note}'")

            # Collect all candidates with their details
            candidates = []
            entity_details = {}

            for entity_result in data["search"]:
                entity_id = entity_result["id"]
                entity_label = entity_result.get("label", "")
                entity_description = entity_result.get("description", "")

                # Get detailed entity information
                entity_details_params = {
                    "action": "wbgetentities",
                    "format": "json",
                    "ids": entity_id,
                    "props": "claims|labels|descriptions",
                    "languages": "en",
                }
                details_response = requests.get(
                    wikidata_api_url, params=entity_details_params, headers=headers, timeout=10
                )
                details_response.raise_for_status()
                details_data = details_response.json()

                if "entities" in details_data and entity_id in details_data["entities"]:
                    entity = details_data["entities"][entity_id]
                    has_image = "P18" in entity.get("claims", {})

                    # Only include entities with images
                    if has_image:
                        # Store full entity details for later use
                        entity_details[entity_id] = entity

                        # Create candidate for AI selection
                        candidates.append(WikidataEntityCandidate(
                            id=entity_id,
                            label=entity_label,
                            description=entity_description,
                            has_image=has_image
                        ))

            if not candidates:
                logger.debug(f"No valid candidates with images found for '{flavor_note}'")
                return None

            # Use AI to select the best entity
            selected_entity_id = await select_best_entity(flavor_note, candidates)

            if not selected_entity_id or selected_entity_id not in entity_details:
                logger.warning(f"AI selection failed, no valid entity selected for '{flavor_note}'")
                return None

            # Process the selected entity
            entity = entity_details[selected_entity_id]
            logger.info(f"Processing selected entity with image for '{flavor_note}': {selected_entity_id}")

            image_filename = entity["claims"]["P18"][0]["mainsnak"]["datavalue"]["value"]
            image_url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{image_filename}"

            # Fetch image attribution from Wikimedia Commons
            commons_api_url = "https://commons.wikimedia.org/w/api.php"
            commons_params = {
                "action": "query",
                "format": "json",
                "prop": "imageinfo",
                "titles": f"File:{image_filename}",
                "iiprop": "extmetadata",
            }

            try:
                commons_response = requests.get(
                    commons_api_url, params=commons_params, headers=headers, timeout=10
                )
                commons_response.raise_for_status()
                commons_data = commons_response.json()

                author = None
                license_short = None
                license_url = None

                try:
                    pages = commons_data.get("query", {}).get("pages", {})
                    for page in pages.values():
                        extmetadata = page.get("imageinfo", [{}])[0].get("extmetadata", {})
                        author = extmetadata.get("Artist", {}).get("value")
                        license_short = extmetadata.get("LicenseShortName", {}).get("value")
                        license_url = extmetadata.get("LicenseUrl", {}).get("value")
                except Exception as e:
                    logger.debug(f"Could not extract image metadata: {e}")

                label = entity.get("labels", {}).get("en", {}).get("value", flavor_note)
                description = (
                    entity.get("descriptions", {}).get("en", {}).get("value", "No description available.")
                )

                return FlavorEntity(
                    flavor_note=flavor_note,
                    source="wikidata",
                    label=label,
                    description=description,
                    id=selected_entity_id,
                    image_url=image_url,
                    image_author=author,
                    image_license=license_short,
                    image_license_url=license_url,
                )
            except requests.exceptions.RequestException as e:
                logger.warning(f"Could not fetch image metadata for {image_filename}: {e}")
                # Still return the entity even without metadata
                label = entity.get("labels", {}).get("en", {}).get("value", flavor_note)
                description = (
                    entity.get("descriptions", {}).get("en", {}).get("value", "No description available.")
                )

                return FlavorEntity(
                    flavor_note=flavor_note,
                    source="wikidata",
                    label=label,
                    description=description,
                    id=selected_entity_id,
                    image_url=image_url,
                    image_author=None,
                    image_license=None,
                    image_license_url=None,
                )

    except requests.exceptions.RequestException as e:
        logger.error(f"Request error for '{flavor_note}': {e}")
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error for '{flavor_note}': {e}")
    except Exception as e:
        logger.error(f"Unexpected error for '{flavor_note}': {e}")

    logger.debug(f"No suitable entity found for '{flavor_note}'")
    return None


# Cache for storing results (since we can't use lru_cache with async functions easily)
_entity_cache = {}

async def find_wikidata_flavor_entity(flavor_note: str) -> FlavorEntity | None:
    """
    Async Wikidata entity finder with manual caching.
    """
    # Check cache first
    if flavor_note in _entity_cache:
        logger.debug(f"Using cached result for '{flavor_note}'")
        return _entity_cache[flavor_note]

    # Get result from async function
    result = await find_wikidata_flavor_entity_async(flavor_note)

    # Cache the result
    _entity_cache[flavor_note] = result

    return result


def create_results_table(results: list[tuple[str, FlavorEntity | None]]) -> Table:
    """Create a Rich table to display search results."""
    table = Table(title="Wikidata Search Results")
    table.add_column("Tasting Note", style="cyan", no_wrap=True)
    table.add_column("Status", style="bold")
    table.add_column("Wikidata ID", style="green")
    table.add_column("Label", style="yellow")
    table.add_column("Image URL", style="blue")

    for tasting_note, entity in results:
        if entity:
            table.add_row(tasting_note, "✅ Found", entity.id, entity.label, entity.image_url)
        else:
            table.add_row(tasting_note, "❌ Not Found", "-", "-", "-")

    return table


async def main():
    """Main async function to run the Wikidata entity search."""
    console.print(Panel.fit("🍃 Kissaten Wikidata Entity Search", style="bold blue"))

    # Path to CSV file
    csv_path = os.path.join(os.path.dirname(__file__), "../src/kissaten/database/tasting_notes_categorized.csv")
    csv_path = os.path.abspath(csv_path)

    logger.info(f"Loading data from: {csv_path}")

    # Read CSV with Polars and build flavor_data
    try:
        df = pl.read_csv(csv_path)
        logger.info(f"Loaded {len(df)} rows from CSV")
    except Exception as e:
        logger.error(f"Failed to load CSV file: {e}")
        console.print(f"[red]Error: Could not load CSV file: {e}[/red]")
        exit(1)

    # Filter and process data
    logger.info("Processing flavor data...")
    df_filtered = df.filter(pl.col("confidence") > 0.7).select(
        ["tasting_note", "tertiary_category", "secondary_category", "primary_category"]
    )

    logger.info(f"Filtered to {len(df_filtered)} high-confidence rows")

    # Convert to set of all unique tasting notes for processing
    all_tasting_notes = set()
    for row in df_filtered.iter_rows():
        # Get all non-empty notes in hierarchy order: tasting_note, tertiary, secondary, primary
        notes = [x.strip() for x in row if x is not None and x.strip()]
        # Add each unique note to our set
        for note in notes:
            all_tasting_notes.add(note)

    logger.info(f"Processing {len(all_tasting_notes)} unique tasting notes")

    # Check for existing results file
    output_file = os.path.join(os.path.dirname(__file__), "../src/kissaten/database/wikidata_flavour_images.json")
    output_file = os.path.abspath(output_file)
    existing_results = {}

    try:
        if os.path.exists(output_file):
            logger.info(f"Found existing results file: {output_file}")
            with open(output_file, encoding="utf-8") as f:
                existing_data = json.load(f)
                existing_results = existing_data.get("results", {})

            # Extract completed tasting notes (keys in the results dict)
            completed_notes = set(existing_results.keys())
            logger.info(f"Found {len(completed_notes)} previously completed tasting notes")

            # Filter out completed notes
            original_count = len(all_tasting_notes)
            all_tasting_notes = all_tasting_notes - completed_notes
            logger.info(f"Filtered out {original_count - len(all_tasting_notes)} completed notes")
            logger.info(f"Remaining notes to process: {len(all_tasting_notes)}")

    except Exception as e:
        logger.warning(f"Could not load existing results file: {e}")
        logger.info("Starting fresh search")

    # Check if there are any entries to process
    if not all_tasting_notes:
        console.print("[yellow]⚠️  All entries have already been processed![/yellow]")
        console.print("[dim]No new searches needed. Check the results file for existing data.[/dim]")
        exit(0)

    # Convert to list for batch processing
    limited_notes = list(all_tasting_notes)
    logger.info(f"Processing {len(limited_notes)} tasting notes in batches of 50")

    # Define batch size
    batch_size = 50
    total_batches = (len(limited_notes) + batch_size - 1) // batch_size

    all_results = existing_results.copy() if existing_results else {}

    # Process in batches
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        overall_task = progress.add_task("Processing all batches...", total=len(limited_notes))

        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(limited_notes))
            batch_notes = limited_notes[start_idx:end_idx]

            console.print(
                f"\n[bold cyan]Processing batch {batch_num + 1}/{total_batches} "
                f"({len(batch_notes)} items)[/bold cyan]"
            )

            batch_task = progress.add_task(f"Batch {batch_num + 1}/{total_batches}...", total=len(batch_notes))
            batch_results = []

            for tasting_note in batch_notes:
                progress.update(batch_task, description=f"Searching: {tasting_note}...")
                progress.update(
                    overall_task, description=f"Batch {batch_num + 1}/{total_batches}: {tasting_note}..."
                )

                logger.info(f"Searching for tasting note: {tasting_note}")
                entity = await find_wikidata_flavor_entity(tasting_note)
                batch_results.append((tasting_note, entity))

                if entity:
                    logger.info(f"✅ Found entity for '{tasting_note}': {entity.label} ({entity.id})")
                else:
                    logger.warning(f"❌ No entity found for '{tasting_note}'")

                progress.advance(batch_task)
                progress.advance(overall_task)

                # Add small delay to be respectful to the API
                await asyncio.sleep(0.5)

            # Save batch results immediately
            try:
                # Add batch results to all_results
                for tasting_note, entity in batch_results:
                    if entity:
                        all_results[tasting_note] = entity.model_dump()
                    else:
                        all_results[tasting_note] = None  # Mark as searched but no result found

                # Calculate statistics for current state
                total_searches = len(all_results)
                successful_matches = sum(1 for entry in all_results.values() if entry is not None)

                results_data = {
                    "metadata": {
                        "total_searches": total_searches,
                        "successful_matches": successful_matches,
                        "success_rate": round(successful_matches / total_searches * 100, 1) if total_searches > 0 else 0,
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "batches_completed": batch_num + 1,
                        "total_batches": total_batches,
                    },
                    "results": all_results,
                }

                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(results_data, f, indent=2, ensure_ascii=False)

                batch_found = sum(1 for _, entity in batch_results if entity is not None)
                console.print(f"[green]✅ Batch {batch_num + 1} completed and saved: {batch_found}/{len(batch_results)} entities found[/green]")

            except Exception as e:
                logger.error(f"Failed to save batch {batch_num + 1} results: {e}")
                console.print(f"[red]❌ Error saving batch {batch_num + 1} results: {e}[/red]")
                # Continue with next batch even if save failed

            progress.remove_task(batch_task)

            # Add a small delay between batches
            if batch_num < total_batches - 1:  # Don't delay after the last batch
                await asyncio.sleep(1.0)

    # Final summary
    console.print("\n[bold green]Final Summary:[/bold green]")

    # Calculate final statistics
    total_searches = len(all_results)
    successful_matches = sum(1 for entry in all_results.values() if entry is not None)
    new_entries_processed = len(limited_notes)

    console.print(f"  [cyan]New entries processed:[/cyan] {new_entries_processed}")
    console.print(f"  [cyan]Total entries in database:[/cyan] {total_searches}")
    console.print(f"  [cyan]Successful matches:[/cyan] {successful_matches}/{total_searches} ({successful_matches / total_searches * 100:.1f}%)")
    console.print(f"  [cyan]Batches completed:[/cyan] {total_batches}")

    console.print(f"\n[green]✅ All processing completed! Results saved to: {output_file}[/green]")
    console.print(f"[dim]All {total_batches} batches processed and saved successfully[/dim]")


if __name__ == "__main__":
    asyncio.run(main())
