#!/usr/bin/env python3
"""Script to count in-stock beans per roaster by reading JSON files directly with DuckDB."""

from pathlib import Path

import duckdb
from rich.console import Console
from rich.table import Table

from kissaten.scrapers import get_registry

console = Console()


def count_beans_from_database(database_path: Path):
    """Count in-stock beans per roaster by reading from existing DuckDB database.

    Args:
        database_path: Path to DuckDB database file
    """
    if not database_path.exists():
        console.print(f"[red]Error: Database file not found at {database_path}[/red]")
        return 1

    try:
        conn = duckdb.connect(str(database_path))

        # Query to get count of in-stock beans per roaster
        query = """
        SELECT
            roaster,
            COUNT(*) as bean_count
        FROM coffee_beans
        WHERE in_stock = true
        GROUP BY roaster
        ORDER BY bean_count DESC, roaster
        """

        results = conn.execute(query).fetchall()

        if not results:
            console.print("[yellow]No in-stock beans found in the database[/yellow]")
            conn.close()
            return 0

        # Create a table for the counts
        table = Table(
            title="[bold cyan]In-Stock Bean Counts by Roaster (from database)[/bold cyan]",
            show_header=True,
            header_style="bold magenta",
            box=None,
            padding=(0, 1),
        )

        table.add_column("Roaster", style="cyan", no_wrap=False)
        table.add_column("Count", style="yellow", justify="right")

        total_beans = 0
        for roaster, count in results:
            table.add_row(roaster, str(count))
            total_beans += count

        console.print()
        console.print(table)
        console.print()
        roaster_plural = "roasters" if len(results) != 1 else "roaster"
        console.print(f"[bold]Total: {total_beans} beans from {len(results)} {roaster_plural}[/bold]")

        conn.close()
        return 0

    except Exception as e:
        console.print(f"[red]Error querying database: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        return 1


def count_beans_from_json(data_dir: Path | None = None):
    """Count in-stock beans per roaster by reading JSON files directly.

    Args:
        data_dir: Path to data directory containing roasters (defaults to 'data/roasters')
    """
    if data_dir is None:
        # Default to data/roasters directory
        data_dir = Path(__file__).parent.parent / "data" / "roasters"

    if not data_dir.exists():
        console.print(f"[red]Error: Data directory not found at {data_dir}[/red]")
        return 1

    try:
        # Find the latest date folder for each roaster
        roaster_latest_dates = {}
        for roaster_dir in data_dir.iterdir():
            if not roaster_dir.is_dir():
                continue

            roaster_name = roaster_dir.name
            date_folders = [d for d in roaster_dir.iterdir() if d.is_dir() and d.name.isdigit()]

            if date_folders:
                # Sort by date folder name (YYYYMMDD format) and get the latest
                latest_date = max(date_folders, key=lambda x: x.name)
                roaster_latest_dates[roaster_name] = latest_date.name

        if not roaster_latest_dates:
            console.print("[yellow]No roaster data found[/yellow]")
            return 0

        # Create an in-memory DuckDB connection
        conn = duckdb.connect(":memory:")

        # Read all JSON files (from all dates)
        json_pattern = str(data_dir / "**" / "*.json")
        conn.execute(f"""
            CREATE OR REPLACE TEMPORARY VIEW all_coffee_data AS
            SELECT
                json_data.*,
                split_part(filename, '/', -3) as roaster_directory,
                split_part(filename, '/', -2) as scrape_date
            FROM read_json('{json_pattern}',
                filename=true,
                auto_detect=true,
                union_by_name=true,
                ignore_errors=true
            ) as json_data
        """)

        # Find latest scrape date for each roaster
        conn.execute("""
            CREATE OR REPLACE TEMPORARY VIEW latest_scrape_dates AS
            SELECT
                roaster_directory,
                MAX(scrape_date) as latest_scrape_date
            FROM all_coffee_data
            GROUP BY roaster_directory
        """)

        # Get all unique beans (most recent version of each URL per roaster)
        conn.execute("""
            CREATE OR REPLACE TEMPORARY VIEW all_unique_beans AS
            SELECT
                acd.*,
                ROW_NUMBER() OVER (
                    PARTITION BY acd.roaster_directory, acd.url
                    ORDER BY acd.scrape_date DESC, acd.scraped_at DESC
                ) as rn
            FROM all_coffee_data acd
            WHERE acd.url IS NOT NULL AND acd.url != ''
        """)

        # Read diffjson files to get stock status updates
        import glob
        diffjson_pattern = str(data_dir / "**" / "*.diffjson")
        diffjson_files_exist = bool(glob.glob(diffjson_pattern, recursive=True))

        if diffjson_files_exist:
            conn.execute(f"""
                CREATE OR REPLACE TEMPORARY VIEW diffjson_data AS
                SELECT
                    json_data.*,
                    split_part(filename, '/', -3) as roaster_directory,
                    split_part(filename, '/', -2) as scrape_date
                FROM read_json('{diffjson_pattern}',
                    filename=true,
                    auto_detect=true,
                    union_by_name=true,
                    ignore_errors=true
                ) as json_data
            """)

            # Get latest diffjson scrape dates
            conn.execute("""
                CREATE OR REPLACE TEMPORARY VIEW latest_diffjson_dates AS
                SELECT
                    roaster_directory,
                    MAX(scrape_date) as latest_scrape_date
                FROM diffjson_data
                GROUP BY roaster_directory
            """)

            # Get URLs from latest diffjson files that are in stock
            conn.execute("""
                CREATE OR REPLACE TEMPORARY VIEW latest_diffjson_in_stock AS
                SELECT DISTINCT
                    dd.roaster_directory,
                    dd.url
                FROM diffjson_data dd
                INNER JOIN latest_diffjson_dates ldd
                    ON dd.roaster_directory = ldd.roaster_directory
                    AND dd.scrape_date = ldd.latest_scrape_date
                WHERE dd.url IS NOT NULL AND dd.url != ''
                  AND (dd.in_stock = true OR dd.in_stock IS NULL)
            """)
        else:
            # Create empty view if no diffjson files
            conn.execute("""
                CREATE OR REPLACE TEMPORARY VIEW latest_diffjson_in_stock AS
                SELECT NULL as roaster_directory, NULL as url
                WHERE false
            """)

        # Get URLs that exist in the latest scrape (these are in-stock)
        conn.execute("""
            CREATE OR REPLACE TEMPORARY VIEW latest_scrape_urls AS
            SELECT DISTINCT
                acd.roaster_directory,
                acd.url
            FROM all_coffee_data acd
            INNER JOIN latest_scrape_dates lsd
                ON acd.roaster_directory = lsd.roaster_directory
                AND acd.scrape_date = lsd.latest_scrape_date
            WHERE acd.url IS NOT NULL AND acd.url != ''
        """)

        # Determine stock status: in-stock if URL exists in latest scrape OR in latest diffjson
        conn.execute("""
            CREATE OR REPLACE TEMPORARY VIEW beans_with_stock_status AS
            SELECT
                aub.*,
                CASE
                    WHEN lsu.url IS NOT NULL OR ldis.url IS NOT NULL THEN true
                    ELSE false
                END as calculated_in_stock
            FROM all_unique_beans aub
            LEFT JOIN latest_scrape_urls lsu
                ON aub.roaster_directory = lsu.roaster_directory
                AND aub.url = lsu.url
            LEFT JOIN latest_diffjson_in_stock ldis
                ON aub.roaster_directory = ldis.roaster_directory
                AND aub.url = ldis.url
            WHERE aub.rn = 1
        """)

        # Get registry to map directory names and roaster names
        registry = get_registry()
        scraper_infos = registry.list_scrapers()
        directory_to_roaster_name = {}
        roaster_name_to_info = {}
        # Also create a normalized mapping (case-insensitive, handle variations)
        roaster_name_variations = {}

        for scraper_info in scraper_infos:
            directory_to_roaster_name[scraper_info.directory_name] = scraper_info.roaster_name
            roaster_name_to_info[scraper_info.roaster_name] = scraper_info
            # Map variations to canonical name
            canonical = scraper_info.roaster_name
            roaster_name_variations[canonical.lower()] = canonical
            roaster_name_variations[canonical] = canonical
            # Also map directory name variations
            roaster_name_variations[scraper_info.directory_name.lower()] = canonical
            roaster_name_variations[scraper_info.directory_name.replace("_", " ").title()] = canonical

        # Count in-stock beans, grouping by both directory and roaster name from JSON
        # This handles cases where directory name doesn't match registry
        query = """
        SELECT
            roaster_directory,
            roaster,
            COUNT(*) as bean_count
        FROM beans_with_stock_status
        WHERE calculated_in_stock = true
        GROUP BY roaster_directory, roaster
        ORDER BY bean_count DESC, roaster_directory, roaster
        """

        results = conn.execute(query).fetchall()

        # Aggregate counts by roaster name (from registry if possible)
        roaster_counts = {}
        for directory_name, roaster_name_json, count in results:
            # Try to find matching registry entry by directory name first
            registry_roaster = directory_to_roaster_name.get(directory_name)

            # If no match by directory, try to match by roaster name from JSON (with variations)
            if not registry_roaster:
                # Try exact match
                if roaster_name_json in roaster_name_to_info:
                    registry_roaster = roaster_name_json
                # Try case-insensitive match
                elif roaster_name_json and roaster_name_json.lower() in roaster_name_variations:
                    registry_roaster = roaster_name_variations[roaster_name_json.lower()]
                # Try directory name formatted as roaster name
                elif directory_name.replace("_", " ").title() in roaster_name_variations:
                    registry_roaster = roaster_name_variations[directory_name.replace("_", " ").title()]

            # Use registry name if found, otherwise use JSON roaster name, fallback to formatted directory
            final_roaster_name = registry_roaster or roaster_name_json or directory_name.replace("_", " ").title()

            # Aggregate counts for the same roaster (in case there are duplicates)
            roaster_counts[final_roaster_name] = roaster_counts.get(final_roaster_name, 0) + count

        # Convert to list and sort
        mapped_results = [(roaster, count) for roaster, count in roaster_counts.items()]
        mapped_results.sort(key=lambda x: (-x[1], x[0]))
        registry_roasters_with_data = set(roaster_counts.keys())

        # Add roasters from registry that have no data (missing/failing scrapers)
        for scraper_info in scraper_infos:
            if scraper_info.roaster_name not in registry_roasters_with_data:
                mapped_results.append((scraper_info.roaster_name, 0))

        # Sort by count again after mapping (in case names changed)
        mapped_results.sort(key=lambda x: (-x[1], x[0]))

        # Create a table for the counts
        table = Table(
            title="[bold cyan]In-Stock Bean Counts by Roaster (from JSON files)[/bold cyan]",
            show_header=True,
            header_style="bold magenta",
            box=None,
            padding=(0, 1),
        )

        table.add_column("Roaster", style="cyan", no_wrap=False)
        table.add_column("Count", style="yellow", justify="right")

        total_beans = 0
        missing_roasters = []
        for roaster, count in mapped_results:
            if count == 0:
                # Style missing roasters differently
                table.add_row(f"[dim]{roaster}[/dim]", "[red]0[/red]")
                missing_roasters.append(roaster)
            else:
                table.add_row(roaster, str(count))
                total_beans += count

        console.print()
        console.print(table)
        console.print()
        roasters_with_data = len(mapped_results) - len(missing_roasters)
        roaster_plural = "roasters" if roasters_with_data != 1 else "roaster"
        console.print(f"[bold]Total: {total_beans} beans from {roasters_with_data} {roaster_plural}[/bold]")
        if missing_roasters:
            missing_plural = "roasters" if len(missing_roasters) != 1 else "roaster"
            console.print(f"[dim]Missing data: {len(missing_roasters)} {missing_plural} with 0 beans (scraper issues)[/dim]")

        conn.close()
        return 0

    except Exception as e:
        console.print(f"[red]Error reading JSON files: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        return 1


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Count in-stock beans per roaster from JSON files or database"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Path to data directory containing roasters (defaults to 'data/roasters'). "
        "Ignored if --database is provided.",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=None,
        help="Path to DuckDB database file. If provided, reads from database instead of JSON files.",
    )

    args = parser.parse_args()

    # If database is provided, use it; otherwise use JSON files
    if args.database:
        return count_beans_from_database(args.database)
    else:
        return count_beans_from_json(data_dir=args.data_dir)


if __name__ == "__main__":
    import sys

    sys.exit(main())

