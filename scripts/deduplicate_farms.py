#!/usr/bin/env python3
"""
Farm Deduplication Script

Processes farm data region-by-region to identify and cluster duplicate farm entries.
Uses conservative matching rules: high name similarity + shared producer names.

Usage:
    python scripts/deduplicate_farms.py                    # Process all countries
    python scripts/deduplicate_farms.py --country CO       # Process only Colombia
    python scripts/deduplicate_farms.py --resume           # Resume from previous state
    python scripts/deduplicate_farms.py --confidence-threshold 0.90  # Adjust manual review threshold
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kissaten.dedup import cluster_farms, storage

console = Console()

# File paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent


def display_cluster_summary(clusters: list[dict], region_name: str) -> None:
    """Display a summary table of clusters found."""
    # Filter to only clusters with >1 entry (actual duplicates)
    multi_clusters = [c for c in clusters if len(c["entries"]) > 1]

    if not multi_clusters:
        console.print(f"[dim]No duplicates found in {region_name}[/dim]")
        return

    console.print(f"\n[bold cyan]📊 Found {len(multi_clusters)} clusters in {region_name}[/bold cyan]")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Canonical Name", style="cyan")
    table.add_column("Variations", style="yellow")
    table.add_column("Beans", justify="right", style="green")
    table.add_column("Confidence", justify="right")

    for cluster in multi_clusters[:10]:  # Show top 10
        variations = len(cluster["entries"])
        canonical = cluster["canonical_name"]
        total_beans = cluster["total_bean_count"]
        confidence = cluster["confidence"]

        # Format confidence with color
        conf_color = "green" if confidence >= 0.85 else "yellow"
        conf_str = f"[{conf_color}]{confidence:.2f}[/{conf_color}]"

        table.add_row(canonical, str(variations), str(total_beans), conf_str)

    console.print(table)


def review_low_confidence_clusters(clusters: list[dict], threshold: float) -> list[dict]:
    """
    Present low-confidence clusters to user for manual review with interactive selection.

    Args:
        clusters: List of cluster dicts
        threshold: Confidence threshold for review (e.g., 0.85)

    Returns:
        List of approved clusters (high confidence + user-approved low confidence)
    """
    import sys
    import tty
    import termios

    low_conf_clusters = [c for c in clusters if len(c["entries"]) > 1 and c["confidence"] < threshold]

    if not low_conf_clusters:
        return clusters

    console.print(f"\n[bold yellow]⚠️  Found {len(low_conf_clusters)} clusters requiring review[/bold yellow]")
    console.print(f"[dim](Confidence < {threshold})[/dim]\n")

    approved_clusters = [c for c in clusters if c["confidence"] >= threshold or len(c["entries"]) == 1]

    for i, cluster in enumerate(low_conf_clusters, 1):
        entries = cluster["entries"]
        selected = [True] * len(entries)  # All selected by default
        current_index = 0

        while True:
            # Clear screen and display cluster info
            console.clear()
            console.print(
                Panel(
                    f"[bold]{cluster['canonical_name']}[/bold]\n"
                    f"Confidence: [yellow]{cluster['confidence']:.2f}[/yellow]\n"
                    f"Region: {cluster.get('region_name', 'Unknown')}\n"
                    f"Total beans: {cluster['total_bean_count']}",
                    title=f"Cluster {i}/{len(low_conf_clusters)}",
                    border_style="yellow",
                )
            )

            console.print(
                "\n[bold cyan]Select entries to merge:[/bold cyan] "
                "[dim](↑/↓: Navigate, Space: Toggle, Enter: Confirm, 'a': Accept all, 'n': Reject all)[/dim]\n"
            )

            # Display entries with checkboxes
            for idx, (entry, is_selected) in enumerate(zip(entries, selected)):
                checkbox = "☑" if is_selected else "☐"
                checkbox_color = "green" if is_selected else "red"
                arrow = "→ " if idx == current_index else "  "
                base_style = "bold" if idx == current_index else ""

                farm_info = Text()
                farm_info.append(f"{arrow}", style=base_style)
                farm_info.append(f"{checkbox} ", style=f"{checkbox_color} {base_style}".strip())
                farm_info.append(f"{entry['farm_name']}", style=base_style)
                farm_info.append(
                    f" ({entry['producer_name'] or 'no producer'}) - {entry['bean_count']} beans",
                    style=f"dim {base_style}".strip(),
                )
                console.print(farm_info)

            # Get user input
            console.print()

            # Read single keypress
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                key = sys.stdin.read(1)

                # Handle escape sequences for arrow keys
                if key == "\x1b":
                    next1, next2 = sys.stdin.read(2)
                    if next1 == "[":
                        if next2 == "A":  # Up arrow
                            key = "up"
                        elif next2 == "B":  # Down arrow
                            key = "down"
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

            if key == "up":
                current_index = (current_index - 1) % len(entries)
            elif key == "down":
                current_index = (current_index + 1) % len(entries)
            elif key == " ":  # Space - toggle selection
                selected[current_index] = not selected[current_index]
            elif key == "a":  # Accept all
                selected = [True] * len(entries)
                break
            elif key == "n":  # Reject all
                selected = [False] * len(entries)
                break
            elif key in ("\r", "\n"):  # Enter - confirm
                break

        # Process selections
        selected_entries = [e for e, sel in zip(entries, selected) if sel]

        if len(selected_entries) == 0:
            # All rejected - split into singletons
            country = cluster.get("country_code")
            region = cluster.get("region_name")
            region_slug = cluster.get("region_slug")

            for entry in entries:
                approved_clusters.append(
                    {
                        "canonical_name": entry["farm_name"],
                        "entries": [entry],
                        "total_bean_count": entry["bean_count"],
                        "confidence": 1.0,
                        "country_code": country,
                        "region_name": region,
                        "region_slug": region_slug,
                    }
                )
        elif len(selected_entries) == len(entries):
            # All selected - keep the cluster as is
            approved_clusters.append(cluster)
        else:
            # Partial selection - create cluster from selected, singletons from unselected
            country = cluster.get("country_code")
            region = cluster.get("region_name")
            region_slug = cluster.get("region_slug")

            # Create cluster from selected entries
            approved_clusters.append(
                {
                    "canonical_name": cluster["canonical_name"],
                    "entries": selected_entries,
                    "total_bean_count": sum(e["bean_count"] for e in selected_entries),
                    "confidence": 1.0,  # Manual review implies confidence
                    "country_code": country,
                    "region_name": region,
                    "region_slug": region_slug,
                }
            )

            # Create singletons from unselected entries
            unselected_entries = [e for e, sel in zip(entries, selected) if not sel]
            for entry in unselected_entries:
                approved_clusters.append(
                    {
                        "canonical_name": entry["farm_name"],
                        "entries": [entry],
                        "total_bean_count": entry["bean_count"],
                        "confidence": 1.0,
                        "country_code": country,
                        "region_name": region,
                        "region_slug": region_slug,
                    }
                )

    console.clear()
    return approved_clusters


def check_region_needs_processing(
    country_code: str, region_slug: str, existing_mappings: list[dict]
) -> tuple[bool, int, int]:
    """
    Check if a region has unmapped farms by comparing DB state to existing mappings.

    Args:
        country_code: ISO country code
        region_slug: Region slug
        existing_mappings: List of existing mapping dicts

    Returns:
        Tuple of (needs_processing, total_farms_in_db, farms_in_mappings)
    """
    # Get current farms from database
    db_farms = storage.get_farms_for_region(country_code, region_slug)
    db_normalized_names = set(db_farms.keys())

    # Get farms from existing mappings for this region
    mapped_names = set()
    for m in existing_mappings:
        if m.get("country") == country_code and m.get("region") == region_slug:
            mapped_names.update(m["normalized_farm_names"])

    # Check if there are unmapped farms
    unmapped_farms = db_normalized_names - mapped_names

    return len(unmapped_farms) > 0, len(db_normalized_names), len(mapped_names)


def process_region(
    country_code: str,
    region_name: str,
    region_slug: str,
    confidence_threshold: float,
    name_threshold: float,
) -> list[dict]:
    """
    Process a single region: fetch farms, cluster, and assign metadata.

    Args:
        country_code: ISO country code
        region_name: Display name for region
        region_slug: Normalized region slug
        confidence_threshold: Threshold for manual review
        name_threshold: Name similarity threshold for matching

    Returns:
        List of approved clusters with region metadata
    """
    farms = storage.get_farms_for_region(country_code, region_slug)

    if not farms:
        return []

    # Prepare representatives for clustering
    # storage.get_farms_for_region returns dict[normalized_name -> list[entries]]
    # We want to cluster these groups, not individual entries (too expensive/redundant)
    farm_representatives = []
    rep_map = {}  # normalized_name -> list[entries]

    for normalized_name, entries in farms.items():
        # Create a representative entry (using the one with most beans or first one)
        # Use a copy to avoid mutating the original data
        rep = entries[0].copy()
        # Sum bean counts and elevation for better accuracy?
        # For matching, we mainly need names. bean_count helps with canonical selection.
        rep["bean_count"] = sum(e["bean_count"] for e in entries)

        farm_representatives.append(rep)
        rep_map[normalized_name] = entries

    # Cluster the representatives
    clusters = cluster_farms(farm_representatives, name_threshold=name_threshold)

    # Expand clusters back to full entries
    final_clusters = []
    for cluster in clusters:
        # The 'entries' in the cluster are the representatives.
        # We need to replace them with the full original lists of entries.
        full_entries = []
        for rep in cluster["entries"]:
            full_entries.extend(rep_map[rep["farm_normalized"]])

        # Re-calculate total metrics based on full entries
        cluster["entries"] = full_entries
        cluster["total_bean_count"] = sum(e["bean_count"] for e in full_entries)

        final_clusters.append(cluster)

    clusters = final_clusters

    # Inject metadata into clusters
    for cluster in clusters:
        cluster["country_code"] = country_code
        cluster["region_name"] = region_name
        cluster["region_slug"] = region_slug

    # Display summary
    display_cluster_summary(clusters, region_name)

    return clusters


def main():
    parser = argparse.ArgumentParser(description="Deduplicate farm names by region")
    parser.add_argument(
        "--country",
        type=str,
        help="Process only specific country (e.g., CO, ET)",
    )
    parser.add_argument(
        "--force-full-update",
        action="store_true",
        help="Ignore existing state and start from scratch",
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.85,
        help="Confidence threshold for manual review (default: 0.85)",
    )
    parser.add_argument(
        "--name-threshold",
        type=float,
        default=0.90,
        help="Name similarity threshold for matching (default: 0.90)",
    )
    parser.add_argument("--manual", action="store_true", help="Launch interactive manual deduplication tool")

    args = parser.parse_args()

    # Manual Mode
    if args.manual:
        from kissaten.dedup.tui import ManualDedupApp

        app = ManualDedupApp(country_code=args.country)
        app.run()
        return

    console.print(
        Panel.fit(
            "[bold cyan]☕ Farm Deduplication System[/bold cyan]\n"
            "Conservative matching: High name similarity + shared producer names",
            border_style="cyan",
        )
    )

    # Ensure mapping output directory exists
    storage.MAPPING_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Load or initialize clusters from existing mappings
    if args.force_full_update:
        if storage.MAPPING_FILE.exists() and not Confirm.ask(
            f"[yellow]Mapping file exists. Overwrite?[/yellow]", default=False
        ):
            console.print("[red]Aborted[/red]")
            return
        all_clusters = []
        existing_mappings = []
    else:
        # Load existing mappings
        existing_mappings = storage.load_mappings(args.country)
        processed_regions = storage.get_processed_regions(args.country)

        if storage.MAPPING_FILE.exists():
            console.print(
                f"[green]✓ Loaded existing mappings ({len(processed_regions)} regions already processed)[/green]"
            )

        # Load ALL existing clusters to preserve mappings from regions we're not reprocessing
        all_clusters = storage.load_all_clusters_from_mappings(args.country)

    # Get ALL regions and check which need processing
    all_regions = storage.get_all_regions(args.country)

    if args.force_full_update:
        regions_to_process = all_regions
    else:
        # Check each region for unmapped farms
        regions_to_process = []
        regions_with_new_farms = []

        for cc, rn, rk in all_regions:
            region_slug = rk.split(":")[1]

            if rk not in processed_regions:
                # Brand new region
                regions_to_process.append((cc, rn, rk))
            else:
                # Previously processed - check for new farms
                needs_processing, total_db, total_mapped = check_region_needs_processing(
                    cc, region_slug, existing_mappings
                )

                if needs_processing:
                    regions_to_process.append((cc, rn, rk))
                    regions_with_new_farms.append((rn, total_db - total_mapped))

        if regions_with_new_farms:
            console.print(f"\n[yellow]Found {len(regions_with_new_farms)} regions with new farms:[/yellow]")
            for region_name, new_count in regions_with_new_farms[:5]:  # Show first 5
                console.print(f"  • {region_name}: +{new_count} new farms")
            if len(regions_with_new_farms) > 5:
                console.print(f"  ... and {len(regions_with_new_farms) - 5} more\n")

    if not regions_to_process:
        console.print("[green]All requested regions already processed![/green]")
    else:
        console.print(f"\n[bold]Processing {len(regions_to_process)} regions...[/bold]\n")

        # Process regions with progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Processing regions...", total=len(regions_to_process))

            for country_code, region_name, region_key in regions_to_process:
                progress.update(task, description=f"[cyan]{country_code}: {region_name}")

                region_slug = region_key.split(":")[1]
                clusters = process_region(
                    country_code,
                    region_name,
                    region_slug,
                    args.confidence_threshold,
                    args.name_threshold,
                )

                # Remove old clusters for this region and add new ones
                all_clusters = [
                    c
                    for c in all_clusters
                    if not (c.get("country_code") == country_code and c.get("region_slug") == region_slug)
                ]
                all_clusters.extend(clusters)

                # Save incrementally to avoid data loss
                storage.save_mappings(all_clusters)

                progress.advance(task)

        console.print("\n[bold green]✓ All regions processed![/bold green]")

    # Manual review phase for low-confidence clusters
    console.print("\n[bold cyan]═══ Manual Review Phase ═══[/bold cyan]")

    low_conf_clusters = [
        c for c in all_clusters if len(c["entries"]) > 1 and c["confidence"] < args.confidence_threshold
    ]

    if low_conf_clusters:
        console.print(f"\n[bold yellow]{len(low_conf_clusters)} clusters need review[/bold yellow]")
        if Confirm.ask("[bold]Start manual review?[/bold]", default=True):
            approved_clusters = review_low_confidence_clusters(all_clusters, args.confidence_threshold)
            all_clusters = approved_clusters
            storage.save_mappings(all_clusters)
    else:
        console.print("[green]No low-confidence clusters found. All merges are high-confidence![/green]")

    # Generate final output
    console.print("\n[bold cyan]Generating final mapping file...[/bold cyan]")
    storage.save_mappings(all_clusters)
    console.print(f"[green]✓ Saved mappings to {storage.MAPPING_FILE}[/green]")

    total_farms = sum(len(c["entries"]) for c in all_clusters)
    merged_farms = sum(len(c["entries"]) for c in all_clusters if len(c["entries"]) > 1)
    unique_farms = len(all_clusters)

    console.print(
        Panel(
            f"[bold]Total farms processed:[/bold] {total_farms}\n"
            f"[bold]Farms in clusters:[/bold] {merged_farms}\n"
            f"[bold]Unique farms (after dedup):[/bold] {unique_farms}\n"
            f"[bold]Reduction:[/bold] {total_farms - unique_farms} duplicates removed",
            title="[bold green]Summary",
            border_style="green",
        )
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user. State has been saved.[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        import traceback

        console.print(traceback.format_exc())
        sys.exit(1)
