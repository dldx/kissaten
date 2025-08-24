"""Main CLI application for Kissaten."""

import asyncio
import json
import logging
import os
from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.json import JSON
from rich.logging import RichHandler
from rich.table import Table

from ..scrapers import get_registry

# Load environment variables from .env file
load_dotenv()


# Initialize CLI app and console
app = typer.Typer(name="kissaten", help="Coffee bean scraper and search application")
console = Console()


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    log_level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)]
    )


@app.command()
def scrape(
    scraper_name: str = typer.Argument(..., help="Name of the scraper to use"),
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        help="Google API key for AI-powered scrapers. If not provided, will use GOOGLE_API_KEY environment variable"
    ),
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="Output directory for scraped data"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging"
    )
):
    """Scrape coffee beans from a specified roaster using the appropriate scraper.

    By default, saves each bean to its own JSON file in the structure:
    data/roasters/<roaster_name>/<datetime>/<bean_uid>.json
    """
    setup_logging(verbose)

    # Get the registry and check if scraper exists
    registry = get_registry()
    scraper_info = registry.get_scraper_info(scraper_name)

    if not scraper_info:
        console.print(f"[red]Error: Unknown scraper '{scraper_name}'[/red]")
        console.print("\nAvailable scrapers:")
        for info in registry.list_scrapers():
            console.print(f"  • {info.name} - {info.display_name}")
        raise typer.Exit(1)

    # Check for API key if required
    if scraper_info.requires_api_key and not api_key and not os.getenv('GOOGLE_API_KEY'):
        console.print(f"[red]Error: {scraper_info.display_name} requires a Google API key for AI extraction.[/red]")
        console.print("Either pass --api-key or set GOOGLE_API_KEY in your environment/")
        console.print(".env file. Example .env file:")
        console.print("[dim]GOOGLE_API_KEY=your-api-key-here[/dim]")
        raise typer.Exit(1)

    console.print(f"[bold green]Starting {scraper_info.display_name} scraper...[/bold green]")

    async def run_scraper():
        # Create scraper instance
        scraper_kwargs = {}
        if scraper_info.requires_api_key:
            scraper_kwargs['api_key'] = api_key

        scraper = registry.create_scraper(scraper_name, **scraper_kwargs)
        if not scraper:
            console.print(f"[red]Failed to create scraper for {scraper_name}[/red]")
            return None

        try:
            async with scraper:
                beans = await scraper.scrape()

                if not beans:
                    console.print("[yellow]No coffee beans found.[/yellow]")
                    return

                # Display results
                console.print(f"\n[bold green]Found {len(beans)} coffee beans:[/bold green]")

                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("Name", style="cyan", no_wrap=True)
                table.add_column("Origin", style="green")
                table.add_column("Price", style="yellow")
                table.add_column("Tasting Notes", style="blue")
                table.add_column("In Stock", style="red")

                for bean in beans:
                    # Format price with correct currency symbol
                    currency_symbols = {"GBP": "£", "USD": "$", "EUR": "€"}
                    currency_symbol = currency_symbols.get(bean.currency or "", bean.currency or "")
                    price_str = f"{currency_symbol}{bean.price}" if bean.price else "N/A"

                    notes_str = ", ".join(bean.tasting_notes[:3]) if bean.tasting_notes else "N/A"
                    stock_str = "✓" if bean.in_stock else "✗" if bean.in_stock is False else "?"

                    table.add_row(
                        bean.name[:30] + "..." if len(bean.name) > 30 else bean.name,
                        str(bean.origin) or "N/A",
                        price_str,
                        notes_str[:30] + "..." if len(notes_str) > 30 else notes_str,
                        stock_str
                    )

                console.print(table)

                # Save files based on options
                saved_files = []

                # Save each bean to its own file using the new directory structure
                output_path = output_dir or Path("data")
                individual_files = scraper.save_beans_individually(beans, output_path)
                saved_files.extend(individual_files)

                console.print(f"\n[green]Saved {len(individual_files)} individual bean files[/green]")

                return beans

        except Exception as e:
            console.print(f"[red]Error during scraping: {e}[/red]")
            raise typer.Exit(1)

    # Run the async scraper
    beans = asyncio.run(run_scraper())

    if beans:
        console.print(f"\n[bold green]Successfully scraped {len(beans)} coffee beans![/bold green]")


@app.command()
def list_scrapers(
    status_filter: str | None = typer.Option(
        None,
        "--status",
        help="Filter by status (available, experimental, deprecated)"
    )
):
    """List available scrapers."""
    registry = get_registry()
    scrapers = registry.list_scrapers(status_filter)

    if not scrapers:
        console.print("[yellow]No scrapers found.[/yellow]")
        return

    console.print("[bold blue]Available scrapers:[/bold blue]")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Name", style="cyan")
    table.add_column("Roaster", style="green")
    table.add_column("Website", style="blue")
    table.add_column("Country", style="magenta")
    table.add_column("Currency", style="yellow")
    table.add_column("API Key", style="red")
    table.add_column("Status", style="bright_green")

    for scraper_info in scrapers:
        status_icon = {
            "available": "✓",
            "experimental": "⚠",
            "deprecated": "✗"
        }.get(scraper_info.status, "?")

        api_key_required = "Yes" if scraper_info.requires_api_key else "No"

        table.add_row(
            scraper_info.name,
            scraper_info.roaster_name,
            scraper_info.website,
            scraper_info.country,
            scraper_info.currency,
            api_key_required,
            f"{status_icon} {scraper_info.status.title()}"
        )

    console.print(table)

    if status_filter:
        console.print(f"\n[dim]Showing scrapers with status: {status_filter}[/dim]")


@app.command()
def test_scraper(
    scraper_name: str = typer.Argument(..., help="Name of scraper to test"),
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        help="Google API key for AI-powered scrapers"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging"
    )
):
    """Test a specific scraper without saving data."""
    setup_logging(verbose)

    # Get the registry and check if scraper exists
    registry = get_registry()
    scraper_info = registry.get_scraper_info(scraper_name)

    if not scraper_info:
        console.print(f"[red]Unknown scraper: {scraper_name}[/red]")
        console.print("\nAvailable scrapers:")
        for info in registry.list_scrapers():
            console.print(f"  • {info.name} - {info.display_name}")
        raise typer.Exit(1)

    console.print(f"[blue]Testing {scraper_info.display_name} scraper...[/blue]")

    async def test_scraper_async():
        # For connection testing, we'll try without API key first
        try:
            scraper_kwargs = {}
            if scraper_info.requires_api_key and api_key:
                scraper_kwargs['api_key'] = api_key

            scraper = registry.create_scraper(scraper_name, **scraper_kwargs)
            if not scraper:
                console.print(f"[red]Failed to create scraper for {scraper_name}[/red]")
                return False

        except ValueError as e:
            if "API key" in str(e) and scraper_info.requires_api_key:
                console.print("[yellow]Note: API key not provided, testing basic connection only[/yellow]")
                # Try creating scraper without API key for basic connection test
                try:
                    scraper = registry.create_scraper(scraper_name)
                    if not scraper:
                        console.print("[red]Could not create scraper even for basic test[/red]")
                        return False
                except Exception:
                    console.print("[yellow]Cannot test without API key - scraper requires authentication[/yellow]")
                    return False
            else:
                console.print(f"[red]Error creating scraper: {e}[/red]")
                return False

        try:
            async with scraper:
                # Test connection
                try:
                    store_urls = scraper.get_store_urls()
                    console.print(f"Store URLs: {store_urls}")
                except Exception as e:
                    console.print(f"[red]Failed to get store URLs: {e}[/red]")
                    return False

                # Fetch first page
                if store_urls:
                    soup = await scraper.fetch_page(store_urls[0])
                    if soup:
                        console.print("[green]✓ Successfully connected to store page[/green]")
                        console.print(f"Page title: {soup.title.string if soup.title else 'No title'}")
                    else:
                        console.print("[red]✗ Failed to fetch store page[/red]")
                        return False
                else:
                    console.print("[red]✗ No store URLs to test[/red]")
                    return False

            return True
        except Exception as e:
            console.print(f"[red]Test failed: {e}[/red]")
            return False

    success = asyncio.run(test_scraper_async())

    if success:
        console.print(f"[green]✓ {scraper_info.display_name} scraper test passed[/green]")
    else:
        console.print(f"[red]✗ {scraper_info.display_name} scraper test failed[/red]")
        raise typer.Exit(1)


@app.command()
def scraper_info(
    scraper_name: str = typer.Argument(..., help="Name of scraper to get info about")
):
    """Show detailed information about a specific scraper."""
    registry = get_registry()
    info = registry.get_scraper_info(scraper_name)

    if not info:
        console.print(f"[red]Unknown scraper: {scraper_name}[/red]")
        console.print("\nAvailable scrapers:")
        for scraper_info in registry.list_scrapers():
            console.print(f"  • {scraper_info.name} - {scraper_info.display_name}")
        raise typer.Exit(1)

    console.print(f"[bold blue]Scraper: {info.display_name}[/bold blue]")
    console.print()

    info_table = Table(show_header=False, box=None)
    info_table.add_column("Property", style="cyan")
    info_table.add_column("Value", style="white")

    info_table.add_row("Name", info.name)
    info_table.add_row("Roaster", info.roaster_name)
    info_table.add_row("Website", info.website)
    info_table.add_row("Country", info.country)
    info_table.add_row("Currency", info.currency)
    info_table.add_row("API Key Required", "Yes" if info.requires_api_key else "No")
    info_table.add_row("Status", info.status.title())
    if info.description:
        info_table.add_row("Description", info.description)

    console.print(info_table)

    console.print(f"\n[dim]Usage: kissaten scrape {info.name}[/dim]")


@app.command()
def show_bean(
    json_file: Path = typer.Argument(..., help="Path to JSON file with scraped data"),
    index: int = typer.Option(0, help="Index of bean to show (0-based, only for combined files)")
):
    """Show detailed information about a specific coffee bean.

    Works with both individual bean files and combined JSON files.
    For individual bean files, the index parameter is ignored.
    """
    try:
        with open(json_file, encoding='utf-8') as f:
            data = json.load(f)

        # Check if this is a single bean file or combined file
        if isinstance(data, dict) and 'name' in data and 'roaster' in data:
            # This is an individual bean file
            console.print(f"[bold green]Coffee Bean: {data.get('name', 'Unknown')}[/bold green]")
            console.print(f"[dim]File: {json_file}[/dim]")
            console.print(JSON.from_data(data))
        elif isinstance(data, list):
            # This is a combined file
            if not data:
                console.print("[yellow]No beans found in file.[/yellow]")
                return

            if index >= len(data):
                console.print(f"[red]Index {index} out of range. File contains {len(data)} beans.[/red]")
                return

            bean = data[index]
            console.print(f"[bold green]Coffee Bean #{index}[/bold green]")
            console.print(f"[dim]File: {json_file}[/dim]")
            console.print(JSON.from_data(bean))
        else:
            console.print("[red]Invalid file format. Expected bean object or array of beans.[/red]")
            raise typer.Exit(1)

    except FileNotFoundError:
        console.print(f"[red]File not found: {json_file}[/red]")
        raise typer.Exit(1)
    except json.JSONDecodeError:
        console.print(f"[red]Invalid JSON file: {json_file}[/red]")
        raise typer.Exit(1)


@app.command()
def list_sessions(
    roaster_name: str = typer.Argument(None, help="Filter by roaster name"),
    data_dir: Path = typer.Option(
        Path("data"),
        "--data-dir",
        help="Data directory to search"
    )
):
    """List available scraping sessions and their bean counts."""
    roasters_dir = data_dir / "roasters"

    if not roasters_dir.exists():
        console.print(f"[yellow]No data directory found at {roasters_dir}[/yellow]")
        return

    sessions_found = []

    # Walk through the directory structure
    for roaster_dir in roasters_dir.iterdir():
        if roaster_dir.is_dir():
            current_roaster = roaster_dir.name

            # Skip if filtering by roaster name
            if roaster_name and roaster_name.lower() not in current_roaster.lower():
                continue

            for session_dir in roaster_dir.iterdir():
                if session_dir.is_dir():
                    # Count JSON files in this session
                    json_files = list(session_dir.glob("*.json"))
                    bean_count = len(json_files)

                    sessions_found.append({
                        "roaster": current_roaster.replace('_', ' ').title(),
                        "session": session_dir.name,
                        "bean_count": bean_count,
                        "path": session_dir
                    })

    if not sessions_found:
        filter_msg = f" for roaster '{roaster_name}'" if roaster_name else ""
        console.print(f"[yellow]No scraping sessions found{filter_msg}.[/yellow]")
        return

    # Sort by roaster, then by session date
    sessions_found.sort(key=lambda x: (x["roaster"], x["session"]), reverse=True)

    console.print("[bold blue]Scraping Sessions:[/bold blue]")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Roaster", style="cyan")
    table.add_column("Session Date/Time", style="green")
    table.add_column("Beans", style="yellow")
    table.add_column("Path", style="dim")

    for session in sessions_found:
        # Format the session datetime for better readability
        session_str = session["session"]
        if len(session_str) == 8:  # YYYYMMDD format
            date_part = session_str[:8]
            formatted_date = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
            session_display = f"{formatted_date}"
        else:
            session_display = session_str

        table.add_row(
            session["roaster"],
            session_display,
            str(session["bean_count"]),
            str(session["path"])
        )

    console.print(table)
    console.print(f"\n[dim]Found {len(sessions_found)} sessions with {sum(s['bean_count'] for s in sessions_found)} total beans[/dim]")


if __name__ == "__main__":
    app()
