#!/usr/bin/env python3
"""Script to fix incorrect roaster names in JSON files."""

import json
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

# Mapping of incorrect names to correct names
ROASTER_NAME_FIXES = {
    "Terarosa Coffee": "Terarosa",
    "TERAROSA": "Terarosa",
    "Aviary Coffee": "Aviary",
    "Frukt Coffee Roasters": "Frukt Coffee",
    "Space Coffee": "Space Coffee Roastery",
}


def fix_roaster_name_in_file(file_path: Path, correct_name: str) -> bool:
    """Fix roaster name in a single JSON file.

    Args:
        file_path: Path to JSON file
        correct_name: Correct roaster name to use

    Returns:
        True if file was modified, False otherwise
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if data.get("roaster") != correct_name:
            data["roaster"] = correct_name
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        return False
    except Exception as e:
        console.print(f"[red]Error processing {file_path}: {e}[/red]")
        return False


def fix_roaster_names(data_dir: Path | None = None):
    """Fix incorrect roaster names in all JSON files.

    Args:
        data_dir: Path to data directory containing roasters (defaults to 'data/roasters')
    """
    if data_dir is None:
        data_dir = Path(__file__).parent.parent / "data" / "roasters"

    if not data_dir.exists():
        console.print(f"[red]Error: Data directory not found at {data_dir}[/red]")
        return 1

    # Find all JSON files
    json_files = list(data_dir.rglob("*.json"))

    if not json_files:
        console.print("[yellow]No JSON files found[/yellow]")
        return 0

    console.print(f"[cyan]Found {len(json_files)} JSON files to check[/cyan]")

    fixed_count = 0
    total_fixed = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Processing files...", total=len(json_files))

        for json_file in json_files:
            progress.update(task, description=f"Processing {json_file.name}...")

            # Check if this file needs fixing
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                current_roaster = data.get("roaster")
                if current_roaster in ROASTER_NAME_FIXES:
                    correct_name = ROASTER_NAME_FIXES[current_roaster]
                    if fix_roaster_name_in_file(json_file, correct_name):
                        fixed_count += 1
                        total_fixed += 1
                        console.print(
                            f"[green]Fixed[/green] {json_file}: "
                            f"'{current_roaster}' -> '{correct_name}'"
                        )
            except Exception as e:
                console.print(f"[red]Error reading {json_file}: {e}[/red]")

            progress.advance(task)

    console.print()
    console.print(f"[bold green]Fixed {fixed_count} files[/bold green]")
    return 0


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Fix incorrect roaster names in JSON files"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Path to data directory containing roasters (defaults to 'data/roasters')",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without actually modifying files",
    )

    args = parser.parse_args()

    if args.dry_run:
        console.print("[yellow]Dry run mode - no files will be modified[/yellow]")
        # TODO: Implement dry-run mode
        return 0

    return fix_roaster_names(data_dir=args.data_dir)


if __name__ == "__main__":
    import sys

    sys.exit(main())

