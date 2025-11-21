#!/usr/bin/env python3
"""Script to check for directory name mismatches between actual directories and registry."""

from pathlib import Path

from rich.console import Console
from rich.table import Table

from kissaten.scrapers import get_registry

console = Console()


def check_directory_mismatches():
    """Check for mismatches between actual directories and registry directory names."""
    registry = get_registry()
    data_dir = Path(__file__).parent.parent / "data" / "roasters"

    if not data_dir.exists():
        console.print(f"[red]Error: Data directory not found at {data_dir}[/red]")
        return 1

    # Get actual directories
    actual_dirs = {d.name for d in data_dir.iterdir() if d.is_dir()}

    # Get expected directories from registry
    registry_dirs = {scraper_info.directory_name for scraper_info in registry.list_scrapers()}

    # Find directories that exist but aren't in registry
    extra_dirs = actual_dirs - registry_dirs

    # Find directories that should exist but don't
    missing_dirs = registry_dirs - actual_dirs

    # Find directories that might be mismatched (similar names)
    mismatches = []
    for actual_dir in actual_dirs:
        if actual_dir not in registry_dirs:
            # Try to find a matching registry entry
            for scraper_info in registry.list_scrapers():
                # Check if it's a variation (e.g., "aviary_coffee" vs "aviary")
                if actual_dir.startswith(scraper_info.directory_name) or scraper_info.directory_name.startswith(actual_dir):
                    mismatches.append({
                        "actual": actual_dir,
                        "expected": scraper_info.directory_name,
                        "roaster": scraper_info.roaster_name,
                        "scraper": scraper_info.name,
                    })
                    break

    # Display results
    if extra_dirs or missing_dirs or mismatches:
        if mismatches:
            table = Table(
                title="[bold yellow]Potential Directory Name Mismatches[/bold yellow]",
                show_header=True,
                header_style="bold magenta",
            )

            table.add_column("Actual Directory", style="red")
            table.add_column("Expected Directory", style="green")
            table.add_column("Roaster Name", style="cyan")
            table.add_column("Scraper", style="dim")

            for mismatch in mismatches:
                table.add_row(
                    mismatch["actual"],
                    mismatch["expected"],
                    mismatch["roaster"],
                    mismatch["scraper"],
                )

            console.print()
            console.print(table)
            console.print()

        if extra_dirs:
            console.print(f"[yellow]Directories not in registry ({len(extra_dirs)}):[/yellow]")
            for dir_name in sorted(extra_dirs):
                console.print(f"  - {dir_name}")

        if missing_dirs:
            console.print(f"[yellow]Expected directories not found ({len(missing_dirs)}):[/yellow]")
            for dir_name in sorted(missing_dirs):
                # Find the roaster name
                for scraper_info in registry.list_scrapers():
                    if scraper_info.directory_name == dir_name:
                        console.print(f"  - {dir_name} ({scraper_info.roaster_name})")
                        break

        return len(mismatches) + len(extra_dirs)
    else:
        console.print("[bold green]✓ All directories match registry![/bold green]")
        console.print(f"[dim]Checked {len(actual_dirs)} directories[/dim]")
        return 0


def main():
    """Main entry point."""
    return check_directory_mismatches()


if __name__ == "__main__":
    import sys

    sys.exit(main())

