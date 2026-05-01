"""Script for deduplicating coffee region names using OpenCage geocoding and Gemini AI."""

import asyncio
import json
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm

from kissaten.ai.region_selector import RegionSelector
from kissaten.api.db import conn
from kissaten.services.geocoding import OpenCageGeocoder


async def deduplicate_regions(
    country_code: str,
    api_key: str | None = None,
    opencage_key: str | None = None,
    dry_run: bool = False,
    batch_size: int = 10,
    min_beans: int = 1,
    interactive: bool = False,
) -> dict:
    """
    Deduplicate regions using OpenCage geocoding and Gemini Flash AI.

    Args:
        country_code: Two-letter ISO 3166-1 alpha-2 country code
        api_key: Google API key for Gemini (optional, uses env var if not provided)
        opencage_key: OpenCage API key (optional, uses env var if not provided)
        dry_run: Preview changes without creating mapping file
        batch_size: Number of regions to process before pausing
        min_beans: Only process regions with at least this many beans
        interactive: Allow manual selection of geocoding results

    Returns:
        Dictionary with statistics about the deduplication run
    """
    console = Console()
    geocoder = OpenCageGeocoder(api_key=opencage_key)
    selector = RegionSelector(api_key=api_key)

    # Load existing mappings if they exist
    mapping_file = Path("src/kissaten/database/region_mappings") / f"{country_code.upper()}.json"
    mappings = {}
    existing_count = 0

    if mapping_file.exists():
        with open(mapping_file, encoding="utf-8") as f:
            mappings = json.load(f)
            existing_count = len(mappings)
        console.print(
            f"[dim]Loaded {existing_count} existing mappings from {mapping_file}[/dim]\n"
        )

    # Get distinct regions for country with elevation data
    query = """
        SELECT
            region,
            COUNT(DISTINCT bean_id) as bean_count,
            COUNT(DISTINCT farm) filter (where farm is not null and farm != '') as farm_count,
            MIN(elevation_min) filter (where elevation_min > 0) as min_elevation,
            MAX(elevation_max) filter (where elevation_max > 0) as max_elevation
        FROM origins
        WHERE country = ?
          AND region IS NOT NULL
          AND region != ''
        GROUP BY region
        HAVING bean_count >= ?
        ORDER BY bean_count DESC
    """
    regions = conn.execute(query, [country_code.upper(), min_beans]).fetchall()

    # Filter out regions that already have mappings
    regions_to_process = [
        (region, bean_count, farm_count, min_elevation, max_elevation)
        for region, bean_count, farm_count, min_elevation, max_elevation in regions
        if region not in mappings
    ]
    skipped_count = len(regions) - len(regions_to_process)

    console.print(
        f"\n[bold blue]Found {len(regions)} regions for {country_code.upper()}[/bold blue]"
    )
    if existing_count > 0:
        console.print(f"[dim]  - {existing_count} already mapped[/dim]")
        console.print(f"[dim]  - {skipped_count} will be skipped[/dim]")
        console.print(
            f"[bold green]  - {len(regions_to_process)} to process[/bold green]"
        )
    else:
        console.print(
            f"[bold green]  - {len(regions_to_process)} to process[/bold green]"
        )
    console.print(f"Min beans filter: {min_beans}")
    console.print(f"Batch size: {batch_size}")
    console.print(f"Interactive mode: {interactive}")
    console.print(f"Dry run: {dry_run}\n")

    if dry_run:
        console.print(
            "[yellow]DRY RUN MODE - No mapping file will be created[/yellow]\n"
        )

    # Statistics tracking
    stats = {
        "total": len(regions_to_process),
        "skipped": skipped_count,
        "success": 0,
        "failed": 0,
        "invalid": 0,  # Regions marked as invalid by AI
        "high_confidence": 0,  # >= 0.7
        "medium_confidence": 0,  # 0.4-0.7
        "low_confidence": 0,  # < 0.4
    }

    # Early exit if nothing to process
    if len(regions_to_process) == 0:
        console.print(
            "[green]✓ All regions already mapped! Nothing to process.[/green]"
        )
        return stats

    # Process in batches
    for batch_idx, i in enumerate(range(0, len(regions_to_process), batch_size)):
        batch = regions_to_process[i : i + batch_size]
        console.print(
            f"[bold]Batch {batch_idx + 1}/{(len(regions_to_process) + batch_size - 1) // batch_size}[/bold]"
        )

        for region, bean_count, farm_count, min_elevation, max_elevation in batch:
            console.print(f"\n[cyan]Processing:[/cyan] {region}")
            console.print(f"  Beans: {bean_count}, Farms: {farm_count}")
            if min_elevation is not None and max_elevation is not None:
                console.print(f"  Elevation range: {min_elevation:.0f}-{max_elevation:.0f}m")

            # Geocode
            geocoding_result = await geocoder.geocode_region(
                region, country_code.upper()
            )

            if not geocoding_result or not geocoding_result.get("results"):
                console.print("  [red]✗ No geocoding results[/red]")
                stats["failed"] += 1
                # Store failed regions to avoid re-processing
                mappings[region] = {
                    "canonical_state": None,
                    "confidence": 0.0,
                    "reasoning": "No geocoding results from OpenCage API",
                    "status": "failed",
                }
                continue

            num_results = len(geocoding_result["results"])
            console.print(f"  [dim]OpenCage returned {num_results} results[/dim]")

            # Select best result with AI, including elevation data
            elevation_range = None
            if min_elevation is not None and max_elevation is not None:
                elevation_range = (min_elevation, max_elevation)

            selection = await selector.select_best_result(
                region, country_code.upper(), geocoding_result["results"], elevation_range
            )

            # Interactive override if confidence is low, or invalid result, or force interactive
            should_prompt = interactive and (selection.confidence < 0.7 or selection.canonical_state is None)

            # Additional check for 'always-prompt' or similar could be added,
            # but for now we'll just allow a way to force it for all results if we wanted.
            # However, the user wants it to ask even for the ones above.
            # To be safe and let user adjust everything, we can change the threshold or logic.
            # If interactive is True, we should probably show what's happening and ask.

            if interactive:
                console.print(f"  [dim]AI Confidence: {selection.confidence:.2f}[/dim]")

                # If it's a "High" confidence but the user still might want to change it (like Kona being mapped to NC instead of Hawaii)
                # we should ask if the user wants to override even if it's "High" confidence.
                if selection.confidence >= 0.7 and selection.canonical_state is not None:
                    if Confirm.ask(
                        f"\nAI found high confidence result: [bold green]{selection.canonical_state}[/bold green]. Do you want to manually adjust this?",
                        default=False,
                    ):
                        should_prompt = True

            if should_prompt:
                console.print(f"\n[bold yellow]Reviewing:[/bold yellow] {region}")
                console.print(f"  AI Suggestion: {selection.canonical_state} (Conf: {selection.confidence:.2f})")
                console.print(f"  AI Reasoning: {selection.reasoning}")

                if Confirm.ask("\nDo you want to manually select a result?", default=False):
                    table = Table(title=f"Geocoding Results for {region}")
                    table.add_column("Index", style="cyan")
                    table.add_column("Formatted Address", style="white")
                    table.add_column("Type", style="magenta")
                    table.add_column("Components", style="blue")

                    for idx, res in enumerate(geocoding_result["results"]):
                        components = res.get("components", {})
                        comp_str = f"{components.get('_type', 'N/A')}: {components.get('state', components.get('county', 'N/A'))}"
                        table.add_row(
                            str(idx),
                            res.get("formatted", "N/A"),
                            res.get("components", {}).get("_type", "N/A"),
                            comp_str,
                        )

                    console.print(table)

                    choice = Prompt.ask(
                        "Enter result index, 'i' to mark invalid, 'k' to skip, 's' to keep AI, or type a new search term",
                        default="s",
                    )

                    if choice == "i":
                        selection.canonical_state = None
                        selection.selected_index = None
                        selection.confidence = 1.0
                        selection.reasoning = "Manually marked as invalid"
                    elif choice == "k":
                        # Mark as skipped to avoid re-processing but don't mark as invalid/success
                        mappings[region] = {
                            "canonical_state": None,
                            "confidence": 0.0,
                            "reasoning": "Manually skipped during interactive processing",
                            "status": "skipped",
                        }
                        continue
                    elif choice == "s":
                        pass  # Keep AI suggestion
                    elif not choice.isdigit():
                        # Treat any non-digit string (except reserved commands) as a new search query
                        while True:
                            new_search = choice
                            console.print(f"  [dim]Searching for: {new_search}[/dim]")
                            geocoding_result = await geocoder.geocode_region(new_search, country_code.upper())
                            if not geocoding_result or not geocoding_result.get("results"):
                                console.print(f"  [red]✗ No results for '{new_search}'[/red]")
                                choice = Prompt.ask("Enter another search term, or 'i' to mark invalid, 'k' to skip")
                                if choice == "i":
                                    selection.canonical_state = None
                                    selection.selected_index = None
                                    selection.confidence = 1.0
                                    selection.reasoning = (
                                        f"Manually marked invalid after failed searches starting with: {new_search}"
                                    )
                                    break
                                elif choice == "k":
                                    mappings[region] = {"status": "skipped"}  # Simplified skip for loop
                                    break
                                continue

                            # Display new results
                            table = Table(title=f"Results for '{new_search}'")
                            table.add_column("Index", style="cyan")
                            table.add_column("Formatted Address", style="white")
                            table.add_column("Type", style="magenta")
                            table.add_column("Components", style="blue")

                            for idx, res in enumerate(geocoding_result["results"]):
                                components = res.get("components", {})
                                comp_str = f"{components.get('_type', 'N/A')}: {components.get('state', components.get('county', 'N/A'))}"
                                table.add_row(
                                    str(idx),
                                    res.get("formatted", "N/A"),
                                    res.get("components", {}).get("_type", "N/A"),
                                    comp_str,
                                )

                            console.print(table)
                            choice = Prompt.ask(
                                "Enter result index, another search term, or 'i' to mark as invalid",
                            )

                            if choice == "i":
                                selection.canonical_state = None
                                selection.selected_index = None
                                selection.confidence = 1.0
                                selection.reasoning = f"Manually marked invalid after searching for: {new_search}"
                                break
                            elif choice.isdigit():
                                selected_idx = int(choice)
                                if selected_idx < len(geocoding_result["results"]):
                                    selected_res = geocoding_result["results"][selected_idx]
                                    state = selected_res.get("components", {}).get("state")
                                    if not state:
                                        state = Prompt.ask("Enter canonical state name for this result")
                                    selection.canonical_state = state
                                    selection.selected_index = selected_idx
                                    selection.confidence = 1.0
                                    selection.reasoning = f"Manually selected after searching for: {new_search}"
                                    break
                                console.print("[red]Invalid index.[/red]")
                                choice = Prompt.ask("Enter valid index or new search term")
                            # Loop continues if choice is a new search term

                        if region in mappings and mappings[region].get("status") == "skipped":
                            continue
                    elif choice.isdigit():
                        # Original results selection
                        selected_idx = int(choice)
                        if selected_idx < len(geocoding_result["results"]):
                            selected_res = geocoding_result["results"][selected_idx]
                            state = selected_res.get("components", {}).get("state")
                            if not state:
                                state = Prompt.ask("Enter canonical state name for this result")
                            selection.canonical_state = state
                            selection.selected_index = selected_idx
                            selection.confidence = 1.0
                            selection.reasoning = "Manually selected from original results"
                        else:
                            console.print("[red]Invalid index.[/red]")
                            # This path could be improved but for now we'll fall through to original logic

                        # Check if region was marked as invalid
                        selected_idx = int(choice)
                        selected_res = geocoding_result["results"][selected_idx]
                        # Try to extract state from components
                        state = selected_res.get("components", {}).get("state")
                        if not state:
                            state = Prompt.ask("Enter canonical state name for this result")

                        selection.canonical_state = state
                        selection.selected_index = selected_idx
                        selection.confidence = 1.0
                        selection.reasoning = "Manually selected from geocoding results"

            # Check if region was marked as invalid
            if selection.canonical_state is None:
                stats["invalid"] += 1
                console.print("  [bold red]✗ Invalid Region[/bold red]")
                console.print(
                    f"  [bold yellow]Confidence:[/bold yellow] {selection.confidence:.2f}"
                )
                console.print(f"  [dim]Reasoning: {selection.reasoning}[/dim]")
                # Store invalid regions with special marker to avoid re-processing
                mappings[region] = {
                    "canonical_state": None,
                    "confidence": selection.confidence,
                    "reasoning": selection.reasoning,
                    "status": "invalid",
                }
                continue

            # Extract metadata from selected result (only for valid regions with a selected index)
            metadata = {}
            if selection.selected_index is not None:
                selected_result = geocoding_result["results"][selection.selected_index]
                metadata = geocoder.extract_metadata({"results": [selected_result]})
            else:
                # AI provided canonical_state without selecting a specific result
                # This can happen when AI determines the state through reasoning
                console.print(
                    "  [dim]Note: No specific result selected, storing without detailed metadata[/dim]"
                )

            # Update statistics
            stats["success"] += 1
            if selection.confidence >= 0.7:
                stats["high_confidence"] += 1
                conf_color = "green"
            elif selection.confidence >= 0.4:
                stats["medium_confidence"] += 1
                conf_color = "yellow"
            else:
                stats["low_confidence"] += 1
                conf_color = "red"

            console.print(
                f"  [bold green]✓ Selected State:[/bold green] {selection.canonical_state}"
            )
            console.print(
                f"  [bold {conf_color}]Confidence:[/bold {conf_color}] {selection.confidence:.2f}"
            )
            console.print(f"  [dim]Reasoning: {selection.reasoning}[/dim]")

            # Add to mapping with full metadata
            mappings[region] = {
                "canonical_state": selection.canonical_state,
                "confidence": selection.confidence,
                "reasoning": selection.reasoning,
                **metadata,  # Spread metadata fields into mapping
            }

            # Rate limiting: OpenCage free tier ~1 req/sec
            await asyncio.sleep(1.5)

        # Save after each batch (for crash recovery)
        if not dry_run:
            mapping_dir = Path("src/kissaten/database/region_mappings")
            mapping_dir.mkdir(parents=True, exist_ok=True)
            mapping_file = mapping_dir / f"{country_code.upper()}.json"

            with open(mapping_file, "w", encoding="utf-8") as f:
                json.dump(mappings, f, indent=2, ensure_ascii=False)

            console.print(f"  [dim]✓ Progress saved ({len(mappings)} mappings)[/dim]")

        console.print()  # Blank line between batches

    # Final save and confirmation message
    if not dry_run:
        mapping_dir = Path("src/kissaten/database/region_mappings")
        mapping_dir.mkdir(parents=True, exist_ok=True)
        mapping_file = mapping_dir / f"{country_code.upper()}.json"

        with open(mapping_file, "w", encoding="utf-8") as f:
            json.dump(mappings, f, indent=2, ensure_ascii=False)

        console.print(f"[bold green]✓ Mapping saved to:[/bold green] {mapping_file}")
        console.print(f"  Total mappings: {len(mappings)}\n")

    # Summary table
    console.print("\n[bold]Summary[/bold]")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", justify="right", style="green")
    table.add_column("Percentage", justify="right")

    total_all_regions = stats["total"] + stats["skipped"]
    table.add_row("Total Regions in Database", str(total_all_regions), "100%")
    if stats["skipped"] > 0:
        table.add_row(
            "Already Mapped (Skipped)",
            str(stats["skipped"]),
            f"{stats['skipped'] / total_all_regions * 100:.1f}%",
            style="dim",
        )
    table.add_row(
        "Processed This Run",
        str(stats["total"]),
        f"{stats['total'] / total_all_regions * 100:.1f}%",
    )
    table.add_row("", "", "")  # Spacer
    table.add_row(
        "Successfully Processed",
        str(stats["success"]),
        f"{stats['success'] / stats['total'] * 100:.1f}%"
        if stats["total"] > 0
        else "0%",
    )
    table.add_row(
        "Failed (No Results)",
        str(stats["failed"]),
        f"{stats['failed'] / stats['total'] * 100:.1f}%" if stats["failed"] > 0 else "0%",
    )
    table.add_row(
        "Invalid (Rejected by AI)",
        str(stats["invalid"]),
        f"{stats['invalid'] / stats['total'] * 100:.1f}%"
        if stats["invalid"] > 0
        else "0%",
    )
    table.add_row("", "", "")  # Spacer
    table.add_row(
        "High Confidence (≥0.7)",
        str(stats["high_confidence"]),
        f"{stats['high_confidence'] / max(stats['success'], 1) * 100:.1f}%",
    )
    table.add_row(
        "Medium Confidence (0.4-0.7)",
        str(stats["medium_confidence"]),
        f"{stats['medium_confidence'] / max(stats['success'], 1) * 100:.1f}%",
    )
    table.add_row(
        "Low Confidence (<0.4)",
        str(stats["low_confidence"]),
        f"{stats['low_confidence'] / max(stats['success'], 1) * 100:.1f}%",
    )

    console.print(table)

    if dry_run:
        console.print("\n[yellow]DRY RUN - No mapping file created[/yellow]")
    else:
        console.print("\n[bold green]✓ Region geocoding complete![/bold green]")
        console.print(f"[dim]Processed {stats['success']} regions[/dim]")
        console.print("[dim]Next step: Restart API server to load new mappings[/dim]")

    # Warn about invalid regions if any found
    if stats["invalid"] > 0:
        console.print(
            f"\n[bold yellow]⚠ Warning:[/bold yellow] {stats['invalid']} region(s) marked as invalid."
        )
        console.print(
            "[dim]These regions should be reviewed manually and corrected in the source data.[/dim]"
        )

    return stats
