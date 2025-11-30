#!/usr/bin/env python3
"""Script to check for roaster name mismatches between registry and BaseScraper initialization."""

import ast
import inspect
from pathlib import Path

from rich.console import Console
from rich.table import Table

from kissaten.scrapers import get_registry

console = Console()


def extract_roaster_name_from_init(file_path: Path) -> str | None:
    """Extract roaster_name from super().__init__() call in a scraper file.

    Args:
        file_path: Path to scraper Python file

    Returns:
        Roaster name string if found, None otherwise
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content)

        # Find the __init__ method
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "__init__":
                # Look for super().__init__() calls
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        # Check if it's a super().__init__() call
                        if (
                            isinstance(child.func, ast.Attribute)
                            and child.func.attr == "__init__"
                        ):
                            # Look for roaster_name keyword argument
                            for keyword in child.keywords:
                                if keyword.arg == "roaster_name":
                                    if isinstance(keyword.value, ast.Constant):
                                        return keyword.value.value
                                    elif isinstance(keyword.value, ast.Str):  # Python < 3.8
                                        return keyword.value.s
        return None
    except Exception as e:
        console.print(f"[red]Error parsing {file_path}: {e}[/red]")
        return None


def check_all_scrapers():
    """Check all scrapers for roaster name mismatches."""
    registry = get_registry()
    scrapers_dir = Path(__file__).parent.parent / "src" / "kissaten" / "scrapers"

    mismatches = []
    matches = []

    for scraper_info in registry.list_scrapers():
        # Get the scraper class file
        scraper_class = scraper_info.scraper_class
        file_path = Path(inspect.getfile(scraper_class))

        # Extract roaster_name from __init__
        init_roaster_name = extract_roaster_name_from_init(file_path)

        registry_roaster_name = scraper_info.roaster_name

        if init_roaster_name is None:
            mismatches.append(
                {
                    "scraper": scraper_info.name,
                    "registry": registry_roaster_name,
                    "init": "NOT FOUND",
                    "file": file_path.name,
                }
            )
        elif init_roaster_name != registry_roaster_name:
            mismatches.append(
                {
                    "scraper": scraper_info.name,
                    "registry": registry_roaster_name,
                    "init": init_roaster_name,
                    "file": file_path.name,
                }
            )
        else:
            matches.append(scraper_info.name)

    # Display results
    if mismatches:
        table = Table(
            title="[bold red]Roaster Name Mismatches[/bold red]",
            show_header=True,
            header_style="bold magenta",
        )

        table.add_column("Scraper", style="cyan")
        table.add_column("Registry Name", style="green")
        table.add_column("Init Name", style="yellow")
        table.add_column("File", style="dim")

        for mismatch in mismatches:
            table.add_row(
                mismatch["scraper"],
                mismatch["registry"],
                mismatch["init"],
                mismatch["file"],
            )

        console.print()
        console.print(table)
        console.print()
        console.print(f"[red]Found {len(mismatches)} mismatch(es)[/red]")
    else:
        console.print("[bold green]✓ All scrapers have matching roaster names![/bold green]")
        console.print(f"[dim]Checked {len(matches)} scrapers[/dim]")

    return len(mismatches)


def main():
    """Main entry point."""
    return check_all_scrapers()


if __name__ == "__main__":
    import sys

    sys.exit(main())

