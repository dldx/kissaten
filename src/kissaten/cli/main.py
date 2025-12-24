"""Main CLI application for Kissaten."""

import asyncio
import inspect
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

import logfire
import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.json import JSON
from rich.logging import RichHandler
from rich.table import Table

from kissaten.scrapers.registry import ScraperInfo

from ..scrapers import get_registry

# Load environment variables from .env file
load_dotenv()


# Initialize CLI app and console
app = typer.Typer(name="kissaten", help="Coffee bean scraper and search application")
console = Console()


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    log_level = logging.DEBUG if verbose else logging.INFO

    # Configure logfire first
    logfire.configure()

    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True), logfire.LogfireLoggingHandler()],
    )


@app.command()
def scrape(
    scraper_name: str = typer.Argument(..., help="Name of the scraper to use"),
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        help="Google API key for AI-powered scrapers. If not provided, will use GOOGLE_API_KEY environment variable",
    ),
    output_dir: Path | None = typer.Option(None, "--output-dir", "-o", help="Output directory for scraped data"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
    force_full_update: bool = typer.Option(
        False,
        "--force-full-update",
        help="Force full AI extraction for all products instead of efficient stock/price updates for existing beans",
    ),
):
    """Scrape coffee beans from a specified roaster using the appropriate scraper.

    By default, the scraper intelligently updates existing coffee beans with stock and price
    changes (using diffjson updates) while performing full AI extraction only for new beans.
    This makes subsequent scrapes much faster and more efficient.

    Use --force-full-update to bypass this optimization and extract all product details again.

    Saves each bean to its own JSON file in the structure:
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
    if scraper_info.requires_api_key and not api_key and not os.getenv("GOOGLE_API_KEY"):
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
            scraper_kwargs["api_key"] = api_key

        scraper = registry.create_scraper(scraper_name, **scraper_kwargs)
        if not scraper:
            console.print(f"[red]Failed to create scraper for {scraper_name}[/red]")
            return None

        try:
            async with scraper:
                # Check if the scraper's scrape method supports force_full_update parameter
                scrape_method = scraper.scrape
                signature = inspect.signature(scrape_method)

                if "force_full_update" in signature.parameters:
                    beans = await scraper.scrape(force_full_update=force_full_update)
                else:
                    if force_full_update:
                        console.print("[yellow]Warning: --force-full-update not supported by this scraper[/yellow]")
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

                    # Format origins - handle the new origins list structure
                    if bean.origins:
                        origins_str = ", ".join(str(origin) for origin in bean.origins)
                    else:
                        origins_str = "N/A"

                    notes_str = ", ".join(bean.tasting_notes[:3]) if bean.tasting_notes else "N/A"
                    stock_str = "✓" if bean.in_stock else "✗" if bean.in_stock is False else "?"

                    table.add_row(
                        bean.name[:30] + "..." if len(bean.name) > 30 else bean.name,
                        origins_str,
                        price_str,
                        notes_str[:30] + "..." if len(notes_str) > 30 else notes_str,
                        stock_str,
                    )

                console.print(table)

                return beans

        except Exception:
            import traceback

            console.print(f"[red]Error during scraping:\n{traceback.format_exc()}[/red]")
            raise typer.Exit(1)

    # Run the async scraper
    beans = asyncio.run(run_scraper())

    if beans:
        console.print(f"\n[bold green]Successfully scraped {len(beans)} coffee beans![/bold green]")


@app.command()
def list_scrapers(
    status_filter: str | None = typer.Option(
        None, "--status", help="Filter by status (available, experimental, deprecated)"
    ),
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
        status_icon = {"available": "✓", "experimental": "⚠", "deprecated": "✗"}.get(scraper_info.status, "?")

        api_key_required = "Yes" if scraper_info.requires_api_key else "No"

        table.add_row(
            scraper_info.name,
            scraper_info.roaster_name,
            scraper_info.website,
            scraper_info.country,
            scraper_info.currency,
            api_key_required,
            f"{status_icon} {scraper_info.status.title()}",
        )

    console.print(table)

    if status_filter:
        console.print(f"\n[dim]Showing scrapers with status: {status_filter}[/dim]")


@app.command()
def test_scraper(
    scraper_name: str = typer.Argument(..., help="Name of scraper to test"),
    api_key: str | None = typer.Option(None, "--api-key", help="Google API key for AI-powered scrapers"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
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
                scraper_kwargs["api_key"] = api_key

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
                    store_urls = await scraper.get_store_urls()
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
def scraper_info(scraper_name: str = typer.Argument(..., help="Name of scraper to get info about")):
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
    index: int = typer.Option(0, help="Index of bean to show (0-based, only for combined files)"),
):
    """Show detailed information about a specific coffee bean.

    Works with both individual bean files and combined JSON files.
    For individual bean files, the index parameter is ignored.
    """
    try:
        with open(json_file, encoding="utf-8") as f:
            data = json.load(f)

        # Check if this is a single bean file or combined file
        if isinstance(data, dict) and "name" in data and "roaster" in data:
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
    data_dir: Path = typer.Option(Path("data"), "--data-dir", help="Data directory to search"),
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

                    sessions_found.append(
                        {
                            "roaster": current_roaster.replace("_", " ").title(),
                            "session": session_dir.name,
                            "bean_count": bean_count,
                            "path": session_dir,
                        }
                    )

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

        table.add_row(session["roaster"], session_display, str(session["bean_count"]), str(session["path"]))

    console.print(table)
    total_beans = sum(s["bean_count"] for s in sessions_found)
    console.print(f"\n[dim]Found {len(sessions_found)} sessions with {total_beans} total beans[/dim]")


@app.command()
def run_all_scrapers(
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        help="Google API key for AI-powered scrapers. If not provided, will use GOOGLE_API_KEY environment variable",
    ),
    output_dir: Path | None = typer.Option(None, "--output-dir", "-o", help="Output directory for scraped data"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
    status_filter: str | None = typer.Option(
        "available", "--status", help="Filter scrapers by status (available, experimental, deprecated, all)"
    ),
    continue_on_error: bool = typer.Option(
        True, "--continue-on-error", help="Continue running other scrapers if one fails"
    ),
    max_concurrent: int = typer.Option(1, "--max-concurrent", help="Maximum number of scrapers to run concurrently"),
):
    """Run all registered scrapers one at a time with session tracking and error logging.

    This command iterates through all registered scrapers and runs them sequentially or
    with limited concurrency. It tracks the success/failure of each scraper session and
    logs errors to Logfire. A scraper is considered failed if no beans are found
    (beans_found = 0) in the session.

    Examples:
        kissaten run-all-scrapers                    # Run all available scrapers
        kissaten run-all-scrapers --status all       # Run scrapers of all statuses
        kissaten run-all-scrapers --max-concurrent 3 # Run up to 3 scrapers concurrently
        kissaten run-all-scrapers --verbose          # Enable verbose logging
    """
    setup_logging(verbose)

    # Get the registry and filter scrapers
    registry = get_registry()
    if status_filter == "all":
        scrapers: list[ScraperInfo] = registry.list_scrapers()
    else:
        scrapers: list[ScraperInfo] = registry.list_scrapers(status_filter)

    if not scrapers:
        filter_msg = f" with status '{status_filter}'" if status_filter != "all" else ""
        console.print(f"[yellow]No scrapers found{filter_msg}.[/yellow]")
        return

    status_msg = f" with status {status_filter}" if status_filter != "all" else ""
    console.print(f"[bold blue]Running {len(scrapers)} scrapers{status_msg}...[/bold blue]")

    # Track overall results
    results = {"successful": [], "failed": [], "skipped": []}

    async def run_scrapers():
        # Create a semaphore to limit concurrent scrapers
        semaphore = asyncio.Semaphore(max_concurrent)
        completed_count = 0

        # Simple progress display without overwriting individual results
        start_msg = f"Starting {len(scrapers)} scrapers (max {max_concurrent} concurrent)..."
        console.print(f"\n[bold blue]{start_msg}[/bold blue]\n")

        async def run_single_scraper(scraper_info):
            nonlocal completed_count
            async with semaphore:
                try:
                    # Log start with console output that persists
                    console.print(f"🔄 [cyan]Starting[/cyan] {scraper_info.display_name} ({scraper_info.roaster_name})")

                    # Check for API key if required
                    api_key_missing = scraper_info.requires_api_key and not api_key and not os.getenv("GOOGLE_API_KEY")
                    if api_key_missing:
                        console.print(f"⏭️  [yellow]Skipped[/yellow] {scraper_info.display_name} - Missing API key")
                        logfire.warn(
                            "Skipping scraper {scraper_name} - requires API key",
                            scraper_name=scraper_info.name,
                            roaster_name=scraper_info.roaster_name,
                            _tags=["scraper_skipped", "missing_api_key"],
                        )
                        results["skipped"].append(
                            {
                                "scraper": scraper_info.name,
                                "roaster": scraper_info.roaster_name,
                                "reason": "Missing API key",
                            }
                        )
                        completed_count += 1
                        console.print(f"[dim]Progress: {completed_count}/{len(scrapers)} completed[/dim]\n")
                        return

                    # Create scraper instance
                    scraper_kwargs = {}
                    if scraper_info.requires_api_key:
                        scraper_kwargs["api_key"] = api_key or os.getenv("GOOGLE_API_KEY")

                    scraper = registry.create_scraper(scraper_info.name, **scraper_kwargs)
                    if not scraper:
                        raise Exception(f"Failed to create scraper for {scraper_info.name}")

                    # Run the scraper with session tracking
                    async with scraper:
                        with logfire.span(
                            "scraper_run",
                            scraper_name=scraper_info.name,
                            roaster_name=scraper_info.roaster_name,
                        ):
                            # Check if scrape method supports force_full_update parameter
                            scrape_method = scraper.scrape
                            signature = inspect.signature(scrape_method)

                            if "force_full_update" in signature.parameters:
                                beans = await scraper.scrape(force_full_update=False)  # Use efficient mode
                            else:
                                beans = await scraper.scrape()

                            # Check session results
                            session = scraper.session
                            if session:
                                beans_found = session.beans_found
                                session_success = session.success

                                # A scraper is considered failed if no beans are found
                                if beans_found == 0:
                                    error_summary = f" - {session.errors[0][:50]}..." if session.errors else ""
                                    fail_msg = f"❌ [red]Failed[/red] {scraper_info.display_name} - No beans found"
                                    fail_msg += error_summary
                                    console.print(fail_msg)

                                    logfire.error(
                                        "Scraper found no beans - potential issue",
                                        scraper_name=scraper_info.name,
                                        roaster_name=scraper_info.roaster_name,
                                        session_id=session.session_id,
                                        beans_found=beans_found,
                                        session_success=session_success,
                                        errors=session.errors,
                                        _tags=["scraper_failed", "no_beans_found"],
                                    )
                                    results["failed"].append(
                                        {
                                            "scraper": scraper_info.name,
                                            "roaster": scraper_info.roaster_name,
                                            "session_id": session.session_id,
                                            "beans_found": beans_found,
                                            "errors": session.errors,
                                            "reason": "No beans found",
                                        }
                                    )
                                else:
                                    stock_count = session.beans_found_in_stock
                                    in_stock_info = f", {stock_count} in stock" if stock_count else ""
                                    success_msg = f"✅ [green]Success[/green] {scraper_info.display_name}"
                                    success_msg += f" - {beans_found} beans"
                                    success_msg += in_stock_info
                                    console.print(success_msg)

                                    logfire.info(
                                        "Scraper completed successfully",
                                        scraper_name=scraper_info.name,
                                        roaster_name=scraper_info.roaster_name,
                                        session_id=session.session_id,
                                        beans_found=beans_found,
                                        beans_processed=session.beans_processed,
                                        beans_in_stock=session.beans_found_in_stock,
                                        session_success=session_success,
                                        _tags=["scraper_success"],
                                    )
                                    results["successful"].append(
                                        {
                                            "scraper": scraper_info.name,
                                            "roaster": scraper_info.roaster_name,
                                            "session_id": session.session_id,
                                            "beans_found": beans_found,
                                            "beans_processed": session.beans_processed,
                                            "beans_in_stock": session.beans_found_in_stock,
                                        }
                                    )
                            else:
                                # No session object - this is unexpected
                                bean_count = len(beans) if beans else 0
                                warn_msg = f"⚠️  [yellow]Warning[/yellow] {scraper_info.display_name}"
                                warn_msg += " - No session object"
                                warn_msg += f", {bean_count} beans"
                                console.print(warn_msg)

                                logfire.warn(
                                    "Scraper has no session object",
                                    scraper_name=scraper_info.name,
                                    roaster_name=scraper_info.roaster_name,
                                    beans_count=bean_count,
                                    _tags=["scraper_warning", "no_session"],
                                )
                                if beans and len(beans) > 0:
                                    results["successful"].append(
                                        {
                                            "scraper": scraper_info.name,
                                            "roaster": scraper_info.roaster_name,
                                            "session_id": "unknown",
                                            "beans_found": len(beans),
                                            "beans_processed": len(beans),
                                            "beans_in_stock": "unknown",
                                        }
                                    )
                                else:
                                    results["failed"].append(
                                        {
                                            "scraper": scraper_info.name,
                                            "roaster": scraper_info.roaster_name,
                                            "session_id": "unknown",
                                            "beans_found": 0,
                                            "errors": ["No session object"],
                                            "reason": "No session and no beans",
                                        }
                                    )

                except Exception as e:
                    error_msg = str(e)
                    # Truncate long error messages for console display
                    short_error = error_msg[:80] + "..." if len(error_msg) > 80 else error_msg
                    console.print(f"💥 [red]Error[/red] {scraper_info.display_name} - {short_error}")

                    logfire.error(
                        "Scraper failed with exception",
                        scraper_name=scraper_info.name,
                        roaster_name=scraper_info.roaster_name,
                        error_message=error_msg,
                        error_type=type(e).__name__,
                        _tags=["scraper_error", "exception"],
                    )
                    results["failed"].append(
                        {
                            "scraper": scraper_info.name,
                            "roaster": scraper_info.roaster_name,
                            "session_id": "unknown",
                            "beans_found": 0,
                            "errors": [error_msg],
                            "reason": f"Exception: {error_msg}",
                        }
                    )

                    if not continue_on_error:
                        raise e

                finally:
                    completed_count += 1
                    console.print(f"[dim]Progress: {completed_count}/{len(scrapers)} completed[/dim]\n")

        # Randomise the order of scrapers to avoid hitting sites in the same order every time
        import random

        random.shuffle(scrapers)
        # Run all scrapers
        await asyncio.gather(*[run_single_scraper(scraper_info) for scraper_info in scrapers])

    # Run the async function
    asyncio.run(run_scrapers())

    # Display final results
    console.print("\n[bold blue]📊 Final Results[/bold blue]")

    results_table = Table(show_header=True, header_style="bold magenta")
    results_table.add_column("Status", style="bold")
    results_table.add_column("Count", style="cyan")
    results_table.add_column("Percentage", style="yellow")

    total = len(scrapers)
    successful_count = len(results["successful"])
    failed_count = len(results["failed"])
    skipped_count = len(results["skipped"])

    results_table.add_row("✅ Successful", str(successful_count), f"{successful_count / total * 100:.1f}%")
    results_table.add_row("❌ Failed", str(failed_count), f"{failed_count / total * 100:.1f}%")
    results_table.add_row("⏭️  Skipped", str(skipped_count), f"{skipped_count / total * 100:.1f}%")
    results_table.add_row("📊 Total", str(total), "100.0%")

    console.print(results_table)

    # Show detailed results for failed scrapers
    if results["failed"]:
        console.print("\n[bold red]❌ Failed Scrapers:[/bold red]")
        failed_table = Table(show_header=True, header_style="bold red")
        failed_table.add_column("Scraper", style="cyan")
        failed_table.add_column("Roaster", style="blue")
        failed_table.add_column("Reason", style="yellow")
        failed_table.add_column("Beans Found", style="magenta")

        for failed in results["failed"]:
            failed_table.add_row(failed["scraper"], failed["roaster"], failed["reason"], str(failed["beans_found"]))
        console.print(failed_table)

    # Show successful scrapers summary
    if results["successful"]:
        console.print("\n[bold green]✅ Successful Scrapers:[/bold green]")
        success_table = Table(show_header=True, header_style="bold green")
        success_table.add_column("Scraper", style="cyan")
        success_table.add_column("Roaster", style="blue")
        success_table.add_column("Beans Found", style="yellow")
        success_table.add_column("In Stock", style="green")

        for success in results["successful"]:
            success_table.add_row(
                success["scraper"],
                success["roaster"],
                str(success["beans_found"]),
                str(success.get("beans_in_stock", "?")),
            )
        console.print(success_table)

    # Log final summary to logfire
    logfire.info(
        "Scraper run completed",
        total_scrapers=total,
        successful_count=successful_count,
        failed_count=failed_count,
        skipped_count=skipped_count,
        success_rate=f"{successful_count / total * 100:.1f}%",
        _tags=["scraper_run_complete", "summary"],
    )

    # Exit with error code if any scrapers failed and continue_on_error is False
    if failed_count > 0 and not continue_on_error:
        console.print(f"\n[red]❌ {failed_count} scrapers failed. Exiting with error code 1.[/red]")
        raise typer.Exit(1)
    elif failed_count > 0:
        console.print(f"\n[yellow]⚠️  {failed_count} scrapers failed, but continuing as requested.[/yellow]")

    success_msg = f"🎉 Scraper run completed! {successful_count}/{total} scrapers successful."
    console.print(f"\n[bold green]{success_msg}[/bold green]")


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind the server to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind the server to"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload for development"),
    log_level: str = typer.Option("info", "--log-level", help="Log level (debug, info, warning, error)"),
    workers: int = typer.Option(1, "--workers", help="Number of worker processes"),
    data_dir: Path = typer.Option(Path("data"), "--data-dir", help="Directory containing scraped data"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
):
    """Start the Kissaten FastAPI backend server.

    This command starts the FastAPI server with automatic data loading from
    the scraped JSON files. The server provides REST API endpoints for
    searching and browsing coffee beans.

    Examples:
        kissaten serve                          # Start on default host:port
        kissaten serve --host 0.0.0.0 --port 8080  # Custom host and port
        kissaten serve --reload                 # Development mode with auto-reload
        kissaten serve --workers 4              # Production with multiple workers
    """
    setup_logging(verbose)

    # Validate data directory
    if not data_dir.exists():
        console.print(f"[red]Error: Data directory '{data_dir}' does not exist.[/red]")
        console.print("Make sure you have scraped some data first using:")
        console.print("[dim]  kissaten scrape <scraper_name>[/dim]")
        raise typer.Exit(1)

    roasters_dir = data_dir / "roasters"
    if not roasters_dir.exists() or not any(roasters_dir.iterdir()):
        console.print(f"[yellow]Warning: No roaster data found in '{roasters_dir}'[/yellow]")
        console.print("The API will start but may not have any data to serve.")

    # Prepare uvicorn command
    app_module = "kissaten.api.main:app"

    cmd = [sys.executable, "-m", "uvicorn", app_module, "--host", host, "--port", str(port), "--log-level", log_level]

    if reload:
        cmd.append("--reload")
        console.print("[yellow]Development mode: Auto-reload enabled[/yellow]")
    else:
        cmd.extend(["--workers", str(workers)])
        if workers > 1:
            console.print(f"[blue]Production mode: {workers} workers[/blue]")

    # Set environment variable for data directory
    env = os.environ.copy()
    env["KISSATEN_DATA_DIR"] = str(data_dir.absolute())

    console.print("[bold green]Starting Kissaten API server...[/bold green]")
    console.print(f"[blue]Host:[/blue] {host}")
    console.print(f"[blue]Port:[/blue] {port}")
    console.print(f"[blue]Data Directory:[/blue] {data_dir.absolute()}")
    console.print(f"[blue]API Documentation:[/blue] http://{host}:{port}/docs")
    console.print(f"[blue]ReDoc Documentation:[/blue] http://{host}:{port}/redoc")
    console.print()
    console.print("[dim]Press Ctrl+C to stop the server[/dim]")

    try:
        # Run uvicorn
        result = subprocess.run(cmd, env=env)
        if result.returncode != 0:
            console.print(f"[red]Server exited with code {result.returncode}[/red]")
            raise typer.Exit(result.returncode)
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped by user[/yellow]")
    except FileNotFoundError:
        console.print("[red]Error: uvicorn not found. Please install it:[/red]")
        console.print("[dim]  pip install uvicorn[/dim]")
        console.print("[dim]  # or[/dim]")
        console.print("[dim]  uv add uvicorn[/dim]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error starting server: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def dev(
    frontend: bool = typer.Option(False, "--frontend", help="Also start the frontend development server"),
    api_port: int = typer.Option(8000, "--api-port", help="Port for the API server"),
    frontend_port: int = typer.Option(5173, "--frontend-port", help="Port for the frontend server"),
    data_dir: Path = typer.Option(Path("data"), "--data-dir", help="Directory containing scraped data"),
):
    """Start development environment with API server and optionally frontend.

    This is a convenience command for development that starts the API server
    in reload mode and optionally the frontend development server.

    Examples:
        kissaten dev                    # API only
        kissaten dev --frontend         # API + Frontend
        kissaten dev --api-port 8080    # Custom API port
    """
    console.print("[bold blue]🚀 Starting Kissaten Development Environment[/bold blue]")

    processes = []

    try:
        # Start API server
        console.print(f"[green]Starting API server on port {api_port}...[/green]")

        env = os.environ.copy()
        env["KISSATEN_DATA_DIR"] = str(data_dir.absolute())

        api_cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "kissaten.api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(api_port),
            "--reload",
            "--log-level",
            "info",
        ]

        api_process = subprocess.Popen(api_cmd, env=env)
        processes.append(("API Server", api_process))

        if frontend:
            # Check if frontend directory exists
            frontend_dir = Path("frontend")
            if not frontend_dir.exists():
                console.print("[yellow]Frontend directory not found, skipping frontend server[/yellow]")
            else:
                console.print(f"[green]Starting frontend server on port {frontend_port}...[/green]")

                # Check for bun first, then npm
                frontend_cmd = None
                if subprocess.run(["which", "bun"], capture_output=True).returncode == 0:
                    frontend_cmd = ["bun", "run", "dev", "--port", str(frontend_port)]
                elif subprocess.run(["which", "npm"], capture_output=True).returncode == 0:
                    frontend_cmd = ["npm", "run", "dev", "--", "--port", str(frontend_port)]

                if frontend_cmd:
                    frontend_process = subprocess.Popen(frontend_cmd, cwd=frontend_dir, env=os.environ.copy())
                    processes.append(("Frontend Server", frontend_process))
                else:
                    console.print("[yellow]Neither bun nor npm found, skipping frontend server[/yellow]")

        console.print()
        console.print("[bold green]✅ Development servers started![/bold green]")
        console.print(f"[blue]API:[/blue] http://127.0.0.1:{api_port}")
        console.print(f"[blue]API Docs:[/blue] http://127.0.0.1:{api_port}/docs")
        if frontend and len(processes) > 1:
            console.print(f"[blue]Frontend:[/blue] http://127.0.0.1:{frontend_port}")
        console.print()
        console.print("[dim]Press Ctrl+C to stop all servers[/dim]")

        # Wait for processes
        try:
            for name, process in processes:
                process.wait()
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopping development servers...[/yellow]")

    except Exception as e:
        console.print(f"[red]Error starting development environment: {e}[/red]")
        raise typer.Exit(1)
    finally:
        # Clean up processes
        for name, process in processes:
            if process.poll() is None:
                console.print(f"[dim]Stopping {name}...[/dim]")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()


@app.command()
def refresh(
    data_dir: Path = typer.Option(Path("data"), "--data-dir", help="Directory containing scraped data"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
    incremental: bool = typer.Option(
        False, "--incremental", "-i", help="Incremental update (only process new/changed files)"
    ),
    check_for_changes: bool = typer.Option(
        False, "--check-for-changes", help="Verify file checksums to detect changes (slower, use with --incremental)"
    ),
):
    """Refresh the database by running db.py as a script to reinitialize and reload all coffee bean data.

    This command runs the db.py script directly, which performs database refresh.

    Two modes are available:

    Full Refresh (default):
    1. Dropping and recreating all database tables
    2. Loading country codes and roaster location data
    3. Loading all coffee bean data from JSON files
    4. Applying processing method mappings
    5. Normalizing country codes
    6. Calculating USD prices
    7. Loading tasting notes categories
    8. Applying any diffjson updates

    Incremental Update (--incremental flag):
    1. Preserves existing database tables and data
    2. Only processes JSON/diffjson files that haven't been processed before
    3. Tracks processed files in processed_files table
    4. Much faster for updates after scraping new beans
    5. Ideal for regular data updates
    6. Assumes files don't change after being added (for speed)

    Check for Changes (--check-for-changes flag, use with --incremental):
    1. Verifies file checksums to detect if files have changed
    2. Reprocesses files that have been modified
    3. Slower than default incremental mode but catches file modifications
    4. Use when files might have been edited or restored from backup

    The script uses the rw_kissaten.duckdb database file when run directly,
    which is important for the proper database initialization flow.

    This is useful after making schema changes or when you want to ensure
    the database is fully up-to-date with all scraped data.

    Examples:
        kissaten refresh                          # Full refresh with default data directory
        kissaten refresh --incremental            # Incremental update (fast, assumes files don't change)
        kissaten refresh --incremental --check-for-changes  # Incremental with checksum verification
        kissaten refresh --data-dir /path/to/data # Use custom data directory
        kissaten refresh --verbose                # Enable verbose output with real-time db.py output
        kissaten refresh -i -v                    # Incremental + verbose
        kissaten refresh -i --check-for-changes -v  # Full incremental with change detection
    """
    setup_logging(verbose)

    # Validate data directory
    roasters_dir = data_dir / "roasters"
    if not roasters_dir.exists():
        console.print(f"[red]Error: Roasters data directory '{roasters_dir}' does not exist.[/red]")
        console.print("Make sure you have scraped some data first using:")
        console.print("[dim]  kissaten scrape <scraper_name>[/dim]")
        raise typer.Exit(1)

    mode_str = "Incremental Update" if incremental else "Full Refresh"
    if incremental and check_for_changes:
        mode_str += " (with checksum verification)"
    console.print(f"[bold blue]🔄 {mode_str}: Kissaten database...[/bold blue]")
    console.print(f"[blue]Data Directory:[/blue] {data_dir.absolute()}")
    console.print(f"[blue]Roasters Directory:[/blue] {roasters_dir.absolute()}")
    console.print(f"[blue]Mode:[/blue] {mode_str}")
    if incremental and not check_for_changes:
        console.print("[dim]Assumes files don't change after being added (for speed)[/dim]")
    elif check_for_changes:
        console.print("[dim]Verifying file checksums to detect changes (slower but thorough)[/dim]")

    try:
        console.print("\n[dim]Initializing database and loading coffee bean data...[/dim]\n")

        # Set environment variable to use rw_kissaten.duckdb for refresh operations
        # This MUST be set before importing db module so it connects to the right database
        os.environ["KISSATEN_USE_RW_DB"] = "1"

        # Import db module AFTER setting environment variable
        from ..api.db import main as db_main

        # Call db.py main function directly instead of subprocess
        asyncio.run(db_main(incremental=incremental, check_for_changes=check_for_changes))

        # Success message and statistics
        mode_desc = "incremental update" if incremental else "full refresh"
        change_check_desc = " with checksum verification" if check_for_changes else ""
        console.print(f"\n[bold green]✅ Database {mode_desc}{change_check_desc} completed successfully![/bold green]")

        # Try to get statistics from the refreshed database
        try:
            import duckdb

            project_root = Path(__file__).parent.parent.parent.parent
            rw_db_path = project_root / "data" / "rw_kissaten.duckdb"

            if rw_db_path.exists():
                with duckdb.connect(str(rw_db_path)) as conn:
                    stats_query = """
                        SELECT
                            COUNT(*) as total_beans,
                            COUNT(*) FILTER (WHERE in_stock = true) as in_stock_beans,
                            COUNT(*) FILTER (WHERE in_stock = false) as out_of_stock_beans,
                            COUNT(DISTINCT roaster) as total_roasters,
                            COUNT(DISTINCT currency) as currencies_used
                        FROM coffee_beans
                    """
                    stats_result = conn.execute(stats_query).fetchone()

                    if stats_result:
                        total, in_stock, out_of_stock, roasters, currencies = stats_result
                        console.print(f"[green]📊 Database Statistics:[/green]")
                        console.print(f"  • Total coffee beans: {total:,}")
                        console.print(f"  • In stock: {in_stock:,}")
                        console.print(f"  • Out of stock: {out_of_stock:,}")
                        console.print(f"  • Total roasters: {roasters}")
                        console.print(f"  • Currencies: {currencies}")
                        console.print(f"  • Database file: {rw_db_path}")
        except Exception as e:
            console.print(f"[yellow]Could not retrieve statistics: {e}[/yellow]")

        console.print()
        console.print("[dim]You can now start the API server with:[/dim]")
        console.print("[dim]  kissaten serve[/dim]")

    except Exception as e:
        console.print(f"[red]Error running database refresh: {e}[/red]")
        if verbose:
            import traceback

            console.print(f"[red]Full error:\n{traceback.format_exc()}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
