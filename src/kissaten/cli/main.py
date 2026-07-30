"""Main CLI application for Kissaten."""

import asyncio
import inspect
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import logfire
import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.json import JSON
from rich.logging import RichHandler
from rich.table import Table

from kissaten.scrapers.registry import ScraperInfo

from ..scrapers import get_registry
from ..ai import processing_method_categorizer, varietal_categorizer, tasting_note_categorizer

# Load environment variables from .env file
load_dotenv()


logger = logging.getLogger(__name__)


# Initialize CLI app and console
app = typer.Typer(name="kissaten", help="Coffee bean scraper and search application")
console = Console()


def _tail_lines(text: str | None, n: int) -> str | None:
    """Return the last ``n`` non-empty lines of ``text``, or None if empty.

    Used to keep subprocess stdout/stderr captured in logfire events short
    enough to be useful (full output can be megabytes) while still showing
    enough to diagnose a failure.
    """
    if not text:
        return None
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return None
    return "\n".join(lines[-n:])


def _subprocess_for_cli(*args: str) -> list[str]:
    """Build a subprocess argv that runs ``kissaten <args>`` portably.

    ``python -m kissaten.cli`` doesn't work because ``kissaten.cli`` is a
    package (no ``__main__``). The console script declared in
    ``pyproject.toml`` is the right entry point, but it depends on PATH. We
    prefer the binary on PATH and fall back to invoking the installed
    Typer ``app`` directly via Python, which works even if PATH is empty
    (cron, containers, etc.).
    """
    binary = shutil.which("kissaten")
    if binary:
        return [binary, *args]
    return [sys.executable, "-c", "from kissaten.cli import app; app()", *args]


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
                    session = scraper.session
                    if session and session.beans_found > 0:
                        console.print(
                            f"[yellow]No new coffee beans scraped (all {session.beans_found} "
                            f"found beans are already up to date).[/yellow]"
                        )
                    else:
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
    num_batches: int = typer.Option(
        1,
        "--num-batches",
        help="Split the shuffled scraper list into N roughly-equal chunks and run only the chunk matching --batch-index. Use 1 (default) to run everything in one go.",
    ),
    batch_index: int = typer.Option(
        0,
        "--batch-index",
        help="0-indexed chunk to run when --num-batches > 1. Must satisfy 0 <= batch-index < num-batches.",
    ),
    date: str | None = typer.Option(
        None,
        "--date",
        help="ISO date (YYYY-MM-DD) used to seed the shuffle. Defaults to today (UTC). Use to replay/backfill a specific day deterministically.",
    ),
    refresh: bool = typer.Option(
        True,
        "--refresh/--no-refresh",
        help="Run `kissaten refresh --incremental` as a subprocess after this batch completes.",
    ),
    validate: bool = typer.Option(
        True,
        "--validate/--no-validate",
        help="Run `kissaten validate-db` after a successful refresh. Validation failures do not fail the batch (the rw DB is still valid) but are logged and surfaced so a bad rw DB is not promoted to production.",
    ),
):
    """Run all registered scrapers one at a time with session tracking and error logging.

    This command iterates through all registered scrapers and runs them sequentially or
    with limited concurrency. It tracks the success/failure of each scraper session and
    logs errors to Logfire. A scraper is considered failed if no beans are found
    (beans_found = 0) in the session.

    Scheduling: with --num-batches N and --batch-index I, only the I-th chunk of a
    date-seeded shuffled list is run. The shuffle is the same for every (date, N) pair,
    so all N cron ticks of one day see the same order but a different order from the
    previous day. See docs/SCHEDULING.md.

    Examples:
        kissaten run-all-scrapers                    # Run all available scrapers
        kissaten run-all-scrapers --status all       # Run scrapers of all statuses
        kissaten run-all-scrapers --max-concurrent 3 # Run up to 3 scrapers concurrently
        kissaten run-all-scrapers --verbose          # Enable verbose logging
        kissaten run-all-scrapers --num-batches 16 --batch-index 0   # Cron batch 0/16
        kissaten run-all-scrapers --num-batches 16 --batch-index 3 --date 2026-07-02  # Replay day
    """
    setup_logging(verbose)

    # Validate batch parameters
    if num_batches < 1:
        console.print(f"[red]Error: --num-batches must be >= 1 (got {num_batches})[/red]")
        raise typer.Exit(1)
    if batch_index < 0 or batch_index >= num_batches:
        console.print(f"[red]Error: --batch-index must be in [0, {num_batches}) (got {batch_index})[/red]")
        raise typer.Exit(1)

    # Resolve the seed date
    from datetime import datetime, timezone

    seed_date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    seed_str = f"kissaten-{seed_date}"

    # Get the registry and filter scrapers
    registry = get_registry()
    if status_filter == "all":
        all_scrapers: list[ScraperInfo] = registry.list_scrapers()
    else:
        all_scrapers: list[ScraperInfo] = registry.list_scrapers(status_filter)

    if not all_scrapers:
        filter_msg = f" with status '{status_filter}'" if status_filter != "all" else ""
        console.print(f"[yellow]No scrapers found{filter_msg}.[/yellow]")
        return

    # Date-seeded shuffle so all batches of one day share the same order
    import random

    rng = random.Random(seed_str)
    rng.shuffle(all_scrapers)

    # Split into N roughly-equal chunks and keep only the requested one
    if num_batches > 1:
        chunks: list[list[ScraperInfo]] = [[] for _ in range(num_batches)]
        for i, scraper in enumerate(all_scrapers):
            chunks[i % num_batches].append(scraper)
        scrapers = chunks[batch_index]
        console.print(
            f"[bold blue]Running batch {batch_index + 1}/{num_batches} "
            f"({len(scrapers)} scrapers, seed={seed_str})...[/bold blue]"
        )
        console.print(
            f"[dim]Scrapers in this batch: {', '.join(s.name for s in scrapers) if scrapers else '(none)'}[/dim]\n"
        )
    else:
        scrapers = all_scrapers
        status_msg = f" with status {status_filter}" if status_filter != "all" else ""
        console.print(f"[bold blue]Running {len(scrapers)} scrapers{status_msg} (seed={seed_str})...[/bold blue]")

    # Track overall results
    results = {"successful": [], "failed": [], "skipped": []}

    # Batch-level context shared by every per-scraper logfire event. The
    # outer "run_all_scrapers_batch" span carries the same attributes, so
    # filtering the logfire UI by batch_index surfaces the full chain.
    batch_ctx: dict = {
        "batch_index": batch_index,
        "num_batches": num_batches,
        "date": seed_date,
        "seed": seed_str,
        "scraper_count": len(scrapers),
    }

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
                # Time the whole per-scraper attempt (including any setup
                # outside the inner "scraper_run" span).
                start_ts = time.monotonic()
                outcome = "unknown"
                try:
                    # Log start with console output that persists
                    console.print(f"🔄 [cyan]Starting[/cyan] {scraper_info.display_name} ({scraper_info.roaster_name})")

                    # Check for API key if required
                    api_key_missing = scraper_info.requires_api_key and not api_key and not os.getenv("GOOGLE_API_KEY")
                    if api_key_missing:
                        console.print(f"⏭️  [yellow]Skipped[/yellow] {scraper_info.display_name} - Missing API key")
                        outcome = "skipped_missing_api_key"
                        logfire.warn(
                            "Skipping scraper {scraper_name} - requires API key",
                            scraper_name=scraper_info.name,
                            roaster_name=scraper_info.roaster_name,
                            **batch_ctx,
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
                            **batch_ctx,
                            _tags=["scraper_run"],
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
                                    outcome = "no_beans_found"

                                    logfire.error(
                                        "Scraper found no beans - potential issue",
                                        scraper_name=scraper_info.name,
                                        roaster_name=scraper_info.roaster_name,
                                        session_id=session.session_id,
                                        beans_found=beans_found,
                                        session_success=session_success,
                                        errors=session.errors,
                                        duration_seconds=round(time.monotonic() - start_ts, 3),
                                        **batch_ctx,
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
                                    outcome = "success"

                                    logfire.info(
                                        "Scraper completed successfully",
                                        scraper_name=scraper_info.name,
                                        roaster_name=scraper_info.roaster_name,
                                        session_id=session.session_id,
                                        beans_found=beans_found,
                                        beans_processed=session.beans_processed,
                                        beans_in_stock=session.beans_found_in_stock,
                                        session_success=session_success,
                                        duration_seconds=round(time.monotonic() - start_ts, 3),
                                        **batch_ctx,
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
                                outcome = "no_session"

                                logfire.warn(
                                    "Scraper has no session object",
                                    scraper_name=scraper_info.name,
                                    roaster_name=scraper_info.roaster_name,
                                    beans_count=bean_count,
                                    duration_seconds=round(time.monotonic() - start_ts, 3),
                                    **batch_ctx,
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
                    outcome = "exception"

                    logfire.error(
                        "Scraper failed with exception",
                        scraper_name=scraper_info.name,
                        roaster_name=scraper_info.roaster_name,
                        error_message=error_msg,
                        error_type=type(e).__name__,
                        duration_seconds=round(time.monotonic() - start_ts, 3),
                        **batch_ctx,
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
                    # Emit a single, normalized completion event so it's easy to
                    # fan-in across scrapers in the logfire UI without depending
                    # on the per-branch messages above.
                    logfire.info(
                        "scraper_run_finished",
                        scraper_name=scraper_info.name,
                        roaster_name=scraper_info.roaster_name,
                        outcome=outcome,
                        duration_seconds=round(time.monotonic() - start_ts, 3),
                        **batch_ctx,
                        _tags=["scraper_run", "finished"],
                    )
                    console.print(f"[dim]Progress: {completed_count}/{len(scrapers)} completed[/dim]\n")

        # Note: scrapers are already date-seeded shuffled + filtered to this batch
        # in the outer function, so we just run them as-is.
        await asyncio.gather(*[run_single_scraper(scraper_info) for scraper_info in scrapers])

    # Wrap the whole batch in a single parent span so per-scraper spans
    # and downstream refresh/validate spans nest under one trace in logfire.
    with logfire.span(
        "run_all_scrapers_batch",
        **batch_ctx,
        max_concurrent=max_concurrent,
        status_filter=status_filter or "available",
        refresh=refresh,
        validate=validate,
        _tags=["scraper_run", "batch"],
    ):
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
            **batch_ctx,
            _tags=["scraper_run_complete", "summary"],
        )

        # Persist a machine-readable batch summary so `kissaten validate-db`
        # can gate promotion on batch health (e.g. refuse to promote after a
        # proxy outage where most scrapers failed).
        batch_results_path = Path("data") / "last_batch_results.json"
        try:
            batch_results_path.parent.mkdir(parents=True, exist_ok=True)
            batch_results = {
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "total_scrapers": total,
                "successful_count": successful_count,
                "failed_count": failed_count,
                "skipped_count": skipped_count,
                "scrapers": [
                    *[
                        {
                            "name": s["scraper"],
                            "roaster": s["roaster"],
                            "outcome": "success",
                            "beans_found": s.get("beans_found", 0),
                        }
                        for s in results["successful"]
                    ],
                    *[
                        {
                            "name": f["scraper"],
                            "roaster": f["roaster"],
                            "outcome": "failed",
                            "beans_found": f.get("beans_found", 0),
                            "reason": f.get("reason", ""),
                            "errors": f.get("errors", [])[:5],
                        }
                        for f in results["failed"]
                    ],
                    *[
                        {
                            "name": s["scraper"],
                            "roaster": s["roaster"],
                            "outcome": "skipped",
                            "reason": s.get("reason", ""),
                        }
                        for s in results["skipped"]
                    ],
                ],
            }
            batch_results_path.write_text(json.dumps(batch_results, indent=2))
            logger.info("Wrote batch results summary to %s", batch_results_path)
        except Exception as e:
            logger.warning("Failed to write batch results summary to %s: %s", batch_results_path, e)

        # Exit with error code if any scrapers failed and continue_on_error is False
        if failed_count > 0 and not continue_on_error:
            console.print(f"\n[red]❌ {failed_count} scrapers failed. Exiting with error code 1.[/red]")
            logfire.error(
                "run_all_scrapers_batch exiting due to scraper failure",
                **batch_ctx,
                failed_count=failed_count,
                _tags=["scraper_run_complete", "exit_error"],
            )
            raise typer.Exit(1)
        elif failed_count > 0:
            console.print(f"\n[yellow]⚠️  {failed_count} scrapers failed, but continuing as requested.[/yellow]")

        success_msg = f"🎉 Scraper run completed! {successful_count}/{total} scrapers successful."
        console.print(f"\n[bold green]{success_msg}[/bold green]")

        # Trigger an incremental DB refresh, then validate the result.
        # Both run as their own child spans under the parent batch span so the
        # full scrape → refresh → validate chain is a single trace in logfire.
        # A non-zero exit from either subprocess is logged but does not change
        # the batch's exit code — scraping itself is the unit of work.
        refresh_succeeded = True
        if refresh:
            refresh_data_dir = output_dir or Path("data")
            console.print(f"\n[bold blue]🔄 Running incremental DB refresh on {refresh_data_dir}...[/bold blue]")
            refresh_started = time.monotonic()
            with logfire.span(
                "db_refresh",
                **batch_ctx,
                data_dir=str(refresh_data_dir),
                _tags=["db_refresh", "subprocess"],
            ):
                try:
                    refresh_result = subprocess.run(
                        _subprocess_for_cli(
                            "refresh",
                            "--incremental",
                            "--data-dir",
                            str(refresh_data_dir),
                        ),
                        check=False,
                        capture_output=True,
                        text=True,
                    )
                    duration = round(time.monotonic() - refresh_started, 3)
                    refresh_succeeded = refresh_result.returncode == 0
                    if refresh_succeeded:
                        console.print("[green]✅ Incremental DB refresh completed.[/green]")
                        logfire.info(
                            "db_refresh succeeded",
                            **batch_ctx,
                            data_dir=str(refresh_data_dir),
                            returncode=refresh_result.returncode,
                            duration_seconds=duration,
                            stdout_tail=_tail_lines(refresh_result.stdout, 20),
                            _tags=["db_refresh", "success"],
                        )
                    else:
                        console.print(
                            f"[yellow]⚠️  Incremental DB refresh exited with code "
                            f"{refresh_result.returncode} (scraping results are still valid).[/yellow]"
                        )
                        logfire.warn(
                            "db_refresh failed",
                            **batch_ctx,
                            data_dir=str(refresh_data_dir),
                            returncode=refresh_result.returncode,
                            duration_seconds=duration,
                            stderr_tail=_tail_lines(refresh_result.stderr, 30),
                            stdout_tail=_tail_lines(refresh_result.stdout, 10),
                            _tags=["db_refresh", "failed"],
                        )
                except Exception as refresh_exc:
                    refresh_succeeded = False
                    console.print(f"[yellow]⚠️  Failed to invoke DB refresh: {refresh_exc}[/yellow]")
                    logfire.error(
                        "db_refresh subprocess raised",
                        **batch_ctx,
                        data_dir=str(refresh_data_dir),
                        error_message=str(refresh_exc),
                        error_type=type(refresh_exc).__name__,
                        _tags=["db_refresh", "subprocess_exception"],
                    )

        # Validate the rw DB so we can refuse to promote a corrupted refresh.
        # We only validate if the refresh itself succeeded; a failed refresh
        # means there's nothing new to check.
        if validate and refresh_succeeded:
            console.print("\n[bold blue]🛡️  Validating rw database...[/bold blue]")
            validate_started = time.monotonic()
            with logfire.span(
                "validate_db_after_batch",
                **batch_ctx,
                _tags=["validate_db", "subprocess"],
            ):
                try:
                    validate_result = subprocess.run(
                        _subprocess_for_cli("validate-db"),
                        check=False,
                        capture_output=True,
                        text=True,
                    )
                    duration = round(time.monotonic() - validate_started, 3)
                    if validate_result.returncode == 0:
                        console.print("[green]✅ Validation passed — rw_kissaten.duckdb is safe to promote.[/green]")
                        logfire.info(
                            "validate_db_after_batch passed",
                            **batch_ctx,
                            returncode=validate_result.returncode,
                            duration_seconds=duration,
                            stdout_tail=_tail_lines(validate_result.stdout, 15),
                            _tags=["validate_db", "after_batch_passed"],
                        )
                    else:
                        console.print(
                            f"[bold red]❌ Validation FAILED (exit {validate_result.returncode}). "
                            f"Do NOT promote rw_kissaten.duckdb to production.[/bold red]"
                        )
                        logfire.error(
                            "validate_db_after_batch failed",
                            **batch_ctx,
                            returncode=validate_result.returncode,
                            duration_seconds=duration,
                            stderr_tail=_tail_lines(validate_result.stderr, 40),
                            stdout_tail=_tail_lines(validate_result.stdout, 30),
                            _tags=["validate_db", "after_batch_failed"],
                        )
                except Exception as validate_exc:
                    console.print(f"[yellow]⚠️  Failed to invoke validate-db: {validate_exc}[/yellow]")
                    logfire.error(
                        "validate_db_after_batch subprocess raised",
                        **batch_ctx,
                        error_message=str(validate_exc),
                        error_type=type(validate_exc).__name__,
                        _tags=["validate_db", "subprocess_exception"],
                    )


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
    refresh_mappings: bool = typer.Option(
        False,
        "--refresh-mappings",
        help="Refresh all canonical/normalized columns from current mapping files (region, farm, process, varietal)",
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

    Refresh Mappings (--refresh-mappings flag):
    1. Reloads all mapping files (region, farm, processing methods, varietals)
    2. Recalculates all canonical/normalized columns across the entire database
    3. Updates slugs and unaccented columns for search
    4. Use after updating any mapping JSON files
    5. Works with both full refresh and incremental mode

    The script uses the rw_kissaten.duckdb database file when run directly,
    which is important for the proper database initialization flow.

    This is useful after making schema changes or when you want to ensure
    the database is fully up-to-date with all scraped data.

    Examples:
        kissaten refresh                          # Full refresh with default data directory
        kissaten refresh --incremental            # Incremental update (fast, assumes files don't change)
        kissaten refresh --incremental --check-for-changes  # Incremental with checksum verification
        kissaten refresh --incremental --refresh-mappings   # Incremental + refresh canonical names
        kissaten refresh --refresh-mappings       # Full refresh + refresh canonical names
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

    if not incremental and refresh_mappings:
        mode_str = "Mapping Refresh"
    else:
        mode_str = "Incremental Update" if incremental else "Full Refresh"
        if incremental and check_for_changes:
            mode_str += " (with checksum verification)"
        if refresh_mappings:
            mode_str += " + Refresh Mappings"

    console.print(f"[bold blue]🔄 {mode_str}: Kissaten database...[/bold blue]")
    console.print(f"[blue]Data Directory:[/blue] {data_dir.absolute()}")
    console.print(f"[blue]Roasters Directory:[/blue] {roasters_dir.absolute()}")
    console.print(f"[blue]Mode:[/blue] {mode_str}")
    if incremental and not check_for_changes:
        console.print("[dim]Assumes files don't change after being added (for speed)[/dim]")
    elif check_for_changes:
        console.print("[dim]Verifying file checksums to detect changes (slower but thorough)[/dim]")

    if refresh_mappings and not incremental:
        console.print("[dim]Only refreshing canonical/normalized columns on existing data (skipping ingestion)[/dim]")
    elif refresh_mappings:
        console.print("[dim]Will refresh all canonical/normalized columns from mapping files[/dim]")

    try:
        if not incremental and refresh_mappings:
            console.print("\n[dim]Refreshing mapping transformations on existing records...[/dim]\n")
        else:
            console.print("\n[dim]Initializing database and loading coffee bean data...[/dim]\n")

        # Set environment variables before importing db module so it connects
        # to the right database. The safety guard in db.py refuses to open
        # rw_kissaten.duckdb with a writable config unless this CLI command
        # opts in, which it does here because writing the rw DB is its purpose.
        os.environ["KISSATEN_ALLOW_PRODUCTION_DB"] = "1"
        os.environ["KISSATEN_USE_RW_DB"] = "1"

        # Import db module AFTER setting environment variable
        from ..api.db import main as db_main

        # Call db.py main function directly instead of subprocess
        asyncio.run(
            db_main(incremental=incremental, check_for_changes=check_for_changes, refresh_mappings=refresh_mappings)
        )

        # Success message and statistics
        if not incremental and refresh_mappings:
            mode_desc = "mapping refresh"
        else:
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
        console.print(
            f"[bold blue]Remember to copy {rw_db_path} to {rw_db_path.parent / 'kissaten.duckdb'} before starting the API server.[/bold blue]"
        )
        console.print("[dim]You can now start the API server with:[/dim]")
        console.print("[dim]  kissaten serve[/dim]")

    except Exception as e:
        console.print(f"[red]Error running database refresh: {e}[/red]")
        if verbose:
            import traceback

            console.print(f"[red]Full error:\n{traceback.format_exc()}[/red]")
        raise typer.Exit(1)


@app.command()
def refresh_media(
    podcast_dir: Path = typer.Option(
        Path("podcast_data"), "--podcast-dir", help="Directory containing podcast analysis JSON files"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
):
    """Refresh the podcast/media database independently from coffee bean data.

    This command rebuilds the podcasts.duckdb database from podcast analysis JSON files.
    It is completely independent from the main coffee bean database refresh.

    Steps performed:
    1. Initializes podcast database tables (episodes, segments, entities)
    2. Loads all .analysis.json files from the podcast data directory
    3. Rebuilds the podcast FTS index for search

    Examples:
        kissaten refresh-media                              # Refresh with default podcast_data/ directory
        kissaten refresh-media --podcast-dir /path/to/data  # Custom podcast data directory
        kissaten refresh-media --verbose                    # Enable verbose output
    """
    setup_logging(verbose)

    if not podcast_dir.exists():
        console.print(f"[red]Error: Podcast data directory '{podcast_dir}' does not exist.[/red]")
        console.print("Make sure you have podcast analysis files generated first using:")
        console.print("[dim]  uv run python scripts/ingest_podcasts.py --episode <transcript_file>[/dim]")
        raise typer.Exit(1)

    # Count analysis files
    analysis_files = list(podcast_dir.glob("**/*.analysis.json"))
    if not analysis_files:
        console.print(f"[yellow]No .analysis.json files found in '{podcast_dir}'[/yellow]")
        console.print("Run the podcast ingestion script first to generate analysis files.")
        raise typer.Exit(1)

    console.print("[bold blue]🎙️  Refreshing podcast/media database...[/bold blue]")
    console.print(f"[blue]Podcast Directory:[/blue] {podcast_dir.absolute()}")
    console.print(f"[blue]Analysis Files:[/blue] {len(analysis_files)}")

    try:
        from ..api.podcast_db import main as podcast_db_main, _get_podcast_database_path

        asyncio.run(podcast_db_main())

        db_path = _get_podcast_database_path()
        console.print(f"\n[bold green]✅ Podcast database refresh completed successfully![/bold green]")
        console.print(f"[blue]Database:[/blue] {db_path}")

    except Exception as e:
        console.print(f"[red]Error refreshing podcast database: {e}[/red]")
        if verbose:
            import traceback

            console.print(f"[red]Full error:\n{traceback.format_exc()}[/red]")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# validate-db
# ---------------------------------------------------------------------------

_DEFAULT_DB_PATH = Path("data/rw_kissaten.duckdb")
_DEFAULT_SNAPSHOT_PATH = Path("data/.last_good_counts.json")

# A. Volume drift tolerances. Snapshot is the only source of truth for "what
# the DB looked like last time validation passed"; if a refresh legitimately
# shrinks the DB (e.g. roasters were removed from the registry), the snapshot
# just needs to be re-baselined via --update-snapshot.
_VOLUME_DRIFT_TOLERANCE = 0.02  # ±2 %

# B. Required-field checks. Today the production DB has zero nulls in these
# columns (verified against rw_kissaten.duckdb on 2026-07-03). Any non-zero
# count is a hard fail.
_REQUIRED_FIELDS = ("name", "roaster", "url", "scraped_at", "in_stock")

# C. Orphan / referential integrity limits.
_MAX_ORPHAN_BEANS = 0
_MAX_ORPHAN_ORIGINS = 0
_MAX_BEANS_WITHOUT_ORIGINS = 25  # 3 in production today; allow ~8x headroom

# D. Normalization invariants. The price→price_usd rule is strict; the
# currency coverage check is informational only.
_MAX_PRICE_WITHOUT_USD = 0

# E. Freshness floor: at least this many beans must have been scraped within
# the last 24 h relative to the latest scrape. Zero means the refresh was a
# no-op and we should not promote the DB.
_MIN_BEANS_SCRAPED_LAST_24H = 1

# F. FTS index divergence. Today 8,487 vs 8,502 = 15 rows; allow up to 200.
_MAX_FTS_DIVERGENCE = 200
# FTS index artifact floors: a healthy index has one docs row per indexed
# bean and a populated terms dictionary. Zero docs or empty terms means the
# FTS index was wiped/rebuilt on empty data — every /search?fts_query=...
# request then returns zero (the symptom of the 2026-07-30 regression).
_MIN_FTS_DOCS = 1
_MIN_FTS_TERMID = 1
# Probe term used by the FTS match probe when no live term is recoverable
# from the data (e.g. an empty beans table). It is a common token that is
# robust to real catalogue churn; the index probe exercises match_bm25, not
# the literal token.
_FTS_PROBE_FALLBACK_TERM = "coffee"

# G. In-stock distribution drift vs snapshot. Thresholds are deliberately
# generous because the baseline is re-baselined manually: they exist to catch
# catastrophe-scale in_stock true→false flips (e.g. scrapers marking whole
# catalogues out of stock after network failures), which row-count checks
# cannot see — not normal day-to-day stock churn.
_INSTOCK_DRIFT_TOLERANCE = 0.30  # global in-stock count drop > 30% fails
_MIN_ROASTER_INSTOCK_FOR_WIPEOUT = 10  # per-roaster wipeout check floor

# H. Batch health: refuse to promote when the last scraping batch mostly
# failed (e.g. proxy outage). A missing/stale batch results file only warns,
# so validation never deadlocks when scraping is paused.
_DEFAULT_BATCH_RESULTS_PATH = Path("data/last_batch_results.json")
_MAX_BATCH_FAILURE_FRACTION = 0.5
_BATCH_RESULTS_MAX_AGE_HOURS = 36


@dataclass
class _CheckResult:
    """Outcome of a single validation check."""

    category: str
    name: str
    passed: bool
    actual: str
    threshold: str
    message: str

    def to_logfire_dict(self) -> dict:
        return {
            "category": self.category,
            "check": self.name,
            "passed": self.passed,
            "actual": self.actual,
            "threshold": self.threshold,
            "message": self.message,
        }


def _load_snapshot(snapshot_path: Path) -> dict | None:
    """Read the last-known-good counts JSON, or return None if missing/invalid."""
    if not snapshot_path.exists():
        return None
    try:
        with open(snapshot_path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or "counts" not in data:
            return None
        return data
    except (json.JSONDecodeError, OSError) as exc:
        logfire.warn(
            "Failed to read validate-db snapshot; treating as missing",
            snapshot_path=str(snapshot_path),
            error_message=str(exc),
            _tags=["validate_db", "snapshot_read_failed"],
        )
        return None


def _save_snapshot(snapshot_path: Path, counts: dict) -> None:
    """Persist the current counts as the new last-known-good baseline."""
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "counts": counts,
    }
    with open(snapshot_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _query_scalar(con, sql: str, *params) -> int:
    """Run a SELECT that returns a single integer; safe against transient errors."""
    result = con.execute(sql, params).fetchone()
    if result is None or result[0] is None:
        return 0
    return int(result[0])


def _query_scalar_str(con, sql: str, *params) -> str | None:
    """Run a SELECT that returns a single string, or None if missing/null."""
    result = con.execute(sql, params).fetchone()
    if result is None or result[0] is None:
        return None
    value = result[0]
    return str(value) if not isinstance(value, str) else value


def _check_volume_drift(con, snapshot: dict | None) -> _CheckResult:
    """A. Compare current table row counts to the last-known-good snapshot."""
    counts = {
        "coffee_beans": _query_scalar(con, "SELECT COUNT(*) FROM coffee_beans"),
        "origins": _query_scalar(con, "SELECT COUNT(*) FROM origins"),
        "roasters": _query_scalar(con, "SELECT COUNT(DISTINCT roaster) FROM coffee_beans"),
        "processed_files": _query_scalar(con, "SELECT COUNT(*) FROM processed_files"),
    }

    if snapshot is None:
        return _CheckResult(
            category="A. Volume drift",
            name="row_counts_vs_snapshot",
            passed=True,
            actual=", ".join(f"{k}={v:,}" for k, v in counts.items()),
            threshold="no snapshot baseline yet",
            message="No last-known-good snapshot found; recording current counts.",
        )

    snapshot_counts = snapshot.get("counts", {})
    worst_drop = 0.0
    failing_keys: list[str] = []
    for key, current in counts.items():
        prior = snapshot_counts.get(key)
        if not prior or prior <= 0:
            continue
        drop = (prior - current) / prior
        if drop > _VOLUME_DRIFT_TOLERANCE:
            worst_drop = max(worst_drop, drop)
            failing_keys.append(f"{key}: {prior:,} -> {current:,} (-{drop * 100:.1f}%)")

    passed = not failing_keys
    return _CheckResult(
        category="A. Volume drift",
        name="row_counts_vs_snapshot",
        passed=passed,
        actual=", ".join(f"{k}={v:,}" for k, v in counts.items()),
        threshold=f"±{_VOLUME_DRIFT_TOLERANCE * 100:.0f}% vs snapshot",
        message=(
            "; ".join(failing_keys)
            if failing_keys
            else f"All within ±{_VOLUME_DRIFT_TOLERANCE * 100:.0f}% of snapshot."
        ),
    )


def _check_required_fields(con) -> _CheckResult:
    """B. Required columns on coffee_beans must all be non-null."""
    null_counts = {
        col: _query_scalar(con, f"SELECT COUNT(*) FROM coffee_beans WHERE {col} IS NULL") for col in _REQUIRED_FIELDS
    }
    failing = {k: v for k, v in null_counts.items() if v > 0}
    return _CheckResult(
        category="B. Required fields",
        name="coffee_beans_no_nulls",
        passed=not failing,
        actual=", ".join(f"{k}={v}" for k, v in null_counts.items()),
        threshold="0 nulls in any required column",
        message=(
            "; ".join(f"{k} has {v} nulls" for k, v in failing.items()) or "All required columns fully populated."
        ),
    )


def _check_referential_integrity(con) -> _CheckResult:
    """C. Beans must reference known roasters, origins must reference beans,
    and most beans should have at least one origin row."""
    orphan_beans = _query_scalar(
        con,
        """
        SELECT COUNT(*) FROM coffee_beans b
        WHERE NOT EXISTS (SELECT 1 FROM roasters r WHERE r.name = b.roaster)
        """,
    )
    orphan_origins = _query_scalar(
        con,
        """
        SELECT COUNT(*) FROM origins o
        LEFT JOIN coffee_beans b ON b.id = o.bean_id
        WHERE b.id IS NULL
        """,
    )
    beans_no_origin = _query_scalar(
        con,
        """
        SELECT COUNT(*) FROM coffee_beans b
        WHERE NOT EXISTS (SELECT 1 FROM origins o WHERE o.bean_id = b.id)
        """,
    )
    failing: list[str] = []
    if orphan_beans > _MAX_ORPHAN_BEANS:
        failing.append(f"orphan_beans={orphan_beans} > {_MAX_ORPHAN_BEANS}")
    if orphan_origins > _MAX_ORPHAN_ORIGINS:
        failing.append(f"orphan_origins={orphan_origins} > {_MAX_ORPHAN_ORIGINS}")
    if beans_no_origin > _MAX_BEANS_WITHOUT_ORIGINS:
        failing.append(f"beans_no_origin={beans_no_origin} > {_MAX_BEANS_WITHOUT_ORIGINS}")
    return _CheckResult(
        category="C. Referential integrity",
        name="bean_roaster_origin_links",
        passed=not failing,
        actual=(f"orphan_beans={orphan_beans}, orphan_origins={orphan_origins}, beans_no_origin={beans_no_origin}"),
        threshold=(
            f"orphan_beans<={_MAX_ORPHAN_BEANS}, orphan_origins<={_MAX_ORPHAN_ORIGINS}, "
            f"beans_no_origin<={_MAX_BEANS_WITHOUT_ORIGINS}"
        ),
        message=("; ".join(failing) or "Referential integrity holds."),
    )


def _check_normalization_invariants(con) -> _CheckResult:
    """D. price_usd must follow price, and currency_rates must cover the
    distinct currencies used in coffee_beans."""
    price_no_usd = _query_scalar(
        con,
        """
        SELECT COUNT(*) FROM coffee_beans
        WHERE price IS NOT NULL AND price_usd IS NULL
        """,
    )
    currencies_in_beans = _query_scalar(
        con,
        "SELECT COUNT(DISTINCT currency) FROM coffee_beans WHERE currency IS NOT NULL",
    )
    currency_rates_rows = _query_scalar(con, "SELECT COUNT(*) FROM currency_rates")
    failing: list[str] = []
    if price_no_usd > _MAX_PRICE_WITHOUT_USD:
        failing.append(f"price_without_usd={price_no_usd} > {_MAX_PRICE_WITHOUT_USD}")
    if currency_rates_rows < currencies_in_beans:
        failing.append(f"currency_rates={currency_rates_rows} < currencies_in_beans={currencies_in_beans}")
    return _CheckResult(
        category="D. Normalization",
        name="price_usd_and_currency_coverage",
        passed=not failing,
        actual=(
            f"price_no_usd={price_no_usd}, "
            f"currencies_in_beans={currencies_in_beans}, "
            f"currency_rates={currency_rates_rows}"
        ),
        threshold=(f"price_no_usd<={_MAX_PRICE_WITHOUT_USD}, currency_rates>=currencies_in_beans"),
        message=("; ".join(failing) or "All normalization invariants hold."),
    )


def _check_freshness(con) -> _CheckResult:
    """E. At least some beans must have been freshly scraped in the last 24h.
    Zero means the refresh was a no-op and we should not promote the DB."""
    beans_last_24h = _query_scalar(
        con,
        """
        SELECT COUNT(*) FROM coffee_beans
        WHERE scraped_at >= (SELECT MAX(scraped_at) FROM coffee_beans) - INTERVAL 1 DAY
        """,
    )
    passed = beans_last_24h >= _MIN_BEANS_SCRAPED_LAST_24H
    return _CheckResult(
        category="E. Freshness",
        name="beans_scraped_recently",
        passed=passed,
        actual=f"beans_scraped_last_24h={beans_last_24h}",
        threshold=f">= {_MIN_BEANS_SCRAPED_LAST_24H}",
        message=(
            "No beans were scraped in the last 24 h; refresh was a no-op."
            if not passed
            else f"{beans_last_24h:,} beans scraped in the last 24 h."
        ),
    )


def _check_fts_index(con) -> _CheckResult:
    """F. The FTS source table should keep pace with coffee_beans within
    a small gap; a large gap means the FTS index rebuild dropped rows."""
    beans = _query_scalar(con, "SELECT COUNT(*) FROM coffee_beans")
    fts = _query_scalar(con, "SELECT COUNT(*) FROM coffee_beans_fts_source")
    divergence = abs(beans - fts)
    passed = divergence <= _MAX_FTS_DIVERGENCE
    return _CheckResult(
        category="F. FTS index",
        name="fts_vs_coffee_beans",
        passed=passed,
        actual=f"beans={beans:,}, fts={fts:,}, divergence={divergence}",
        threshold=f"divergence<={_MAX_FTS_DIVERGENCE}",
        message=(
            f"FTS source diverges from coffee_beans by {divergence} rows."
            if not passed
            else f"FTS source within {divergence} rows of coffee_beans."
        ),
    )


def _check_fts_index_tables(con) -> _CheckResult:
    """F2. The FTS index artifacts (``fts_main_<src>.docs``/``.terms``) must
    exist and keep pace with ``coffee_beans_fts_source``.

    The source-table count check (F1) would still pass if ``ensure_fts_index``
    rebuilt against empty tables (leaving an empty docs table); the
    /search?fts_query endpoint would then return zero for every query. This
    check catches that subtler failure mode by inspecting the artifacts the
    extension produced.
    """
    rows = con.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'fts_main_coffee_beans_fts_source'"
    ).fetchall()
    tables_present = {r[0] for r in rows}
    required = {"docs", "terms"}
    missing = required - tables_present
    if missing:
        return _CheckResult(
            category="F. FTS index",
            name="fts_index_tables",
            passed=False,
            actual=f"missing_tables={sorted(missing)}",
            threshold=f"present>={sorted(required)}",
            message=(
                "FTS index artifacts are missing. The /search endpoint will "
                "return zero results for every fts_query. Run `kissaten refresh` "
                "to rebuild the FTS index."
            ),
        )

    fts_source = _query_scalar(con, "SELECT COUNT(*) FROM coffee_beans_fts_source")
    docs = _query_scalar(con, "SELECT COUNT(*) FROM fts_main_coffee_beans_fts_source.docs")
    termid_rows = _query_scalar(
        con,
        "SELECT COUNT(DISTINCT termid) FROM fts_main_coffee_beans_fts_source.terms",
    )

    docs_pass = docs >= min(_MIN_FTS_DOCS, fts_source or _MIN_FTS_DOCS) and abs(fts_source - docs) <= _MAX_FTS_DIVERGENCE
    terms_pass = termid_rows >= _MIN_FTS_TERMID

    passed = docs_pass and terms_pass
    return _CheckResult(
        category="F. FTS index",
        name="fts_index_tables",
        passed=passed,
        actual=f"fts_source={fts_source:,}, docs={docs:,}, termids={termid_rows:,}",
        threshold=(
            f"docs within {_MAX_FTS_DIVERGENCE} of fts_source and >0, "
            f"distinct termids>={_MIN_FTS_TERMID}"
        ),
        message=(
            f"FTS artifacts out of range (fts_source={fts_source}, docs={docs}, termids={termid_rows}). "
            "Run `kissaten refresh` to rebuild the FTS index."
            if not passed
            else f"FTS artifacts healthy (docs={docs}, termids={termid_rows})."
        ),
    )


def _check_fts_match_probe(con) -> _CheckResult:
    """F3. Functional probe: ``match_bm25`` must return at least one hit for a
    token we know is in the catalogue.

    Picking the probe term from a live bean name (rather than hard-coding a
    word) keeps the probe robust to roaster churn; if no name is recoverable
    we fall back to a fixed term. Running the same ``match_bm25`` call shape
    as the /search endpoint (api/main.py:288) means this check exercises the
    exact failure mode users reported (every fts_query returning zero).
    """
    try:
        con.execute("LOAD fts;")
    except duckdb.Error as exc:
        return _CheckResult(
            category="F. FTS index",
            name="fts_match_probe",
            passed=False,
            actual=f"load_failed={type(exc).__name__}",
            threshold="LOAD fts succeeded on read-only connection",
            message=(
                "Could not LOAD the FTS extension; /search?fts_query=... is "
                "unavailable. Ensure the fts extension is installed."
            ),
        )

    probe_term = _query_scalar_str(
        con,
        "SELECT COALESCE(NULLIF(name, ''), ?) FROM coffee_beans WHERE name IS NOT NULL LIMIT 1",
        _FTS_PROBE_FALLBACK_TERM,
    )
    if not probe_term:
        probe_term = _FTS_PROBE_FALLBACK_TERM

    try:
        hits = _query_scalar(
            con,
            "SELECT COUNT(*) FROM (SELECT id, "
            "fts_main_coffee_beans_fts_source.match_bm25(id, ?) AS s "
            "FROM coffee_beans_fts_source) WHERE s IS NOT NULL",
            probe_term,
        )
    except duckdb.Error as exc:
        return _CheckResult(
            category="F. FTS index",
            name="fts_match_probe",
            passed=False,
            actual=f"match_bm25_error={type(exc).__name__}",
            threshold="match_bm25 returns >=1 hit",
            message=(
                f"match_bm25 raised {type(exc).__name__}: {exc}. The /search "
                "endpoint will fail for every fts_query."
            ),
        )

    passed = hits >= 1
    return _CheckResult(
        category="F. FTS index",
        name="fts_match_probe",
        passed=passed,
        actual=f"probe={probe_term!r}, hits={hits}",
        threshold="hits>=1",
        message=(
            f"FTS match probe returned {hits} hit(s) for {probe_term!r}; "
            "the /search endpoint cannot serve FTS queries."
            if not passed
            else f"FTS match probe returned {hits} hit(s) for {probe_term!r}."
        ),
    )


def _check_instock_drift(con, snapshot: dict | None) -> _CheckResult:
    """G. In-stock counts (global and per-roaster) vs the last-known-good
    snapshot. A mass in_stock true→false flip leaves row counts unchanged, so
    check A cannot see it; this check can."""
    in_stock_total = _query_scalar(con, "SELECT COUNT(*) FROM coffee_beans WHERE in_stock = true")
    rows = con.execute("SELECT roaster, COUNT(*) FROM coffee_beans WHERE in_stock = true GROUP BY roaster").fetchall()
    in_stock_by_roaster = {row[0]: int(row[1]) for row in rows}

    snapshot_counts = (snapshot or {}).get("counts", {})
    prior_total = snapshot_counts.get("in_stock_beans")
    prior_by_roaster = snapshot_counts.get("in_stock_by_roaster") or {}

    if not prior_total or prior_total <= 0:
        return _CheckResult(
            category="G. In-stock drift",
            name="instock_counts_vs_snapshot",
            passed=True,
            actual=f"in_stock={in_stock_total:,}",
            threshold="no in-stock baseline yet",
            message="Snapshot has no in-stock baseline; re-baseline with --update-snapshot.",
        )

    failing: list[str] = []
    drop = (prior_total - in_stock_total) / prior_total
    if drop > _INSTOCK_DRIFT_TOLERANCE:
        failing.append(f"in_stock: {prior_total:,} -> {in_stock_total:,} (-{drop * 100:.1f}%)")

    wiped = [
        f"{roaster}: {prior} -> 0"
        for roaster, prior in prior_by_roaster.items()
        if prior >= _MIN_ROASTER_INSTOCK_FOR_WIPEOUT and in_stock_by_roaster.get(roaster, 0) == 0
    ]
    failing.extend(wiped[:10])
    if len(wiped) > 10:
        failing.append(f"...and {len(wiped) - 10} more wiped-out roasters")

    passed = not failing
    return _CheckResult(
        category="G. In-stock drift",
        name="instock_counts_vs_snapshot",
        passed=passed,
        actual=f"in_stock={in_stock_total:,}, roasters_with_stock={len(in_stock_by_roaster)}",
        threshold=(
            f"global drop<={_INSTOCK_DRIFT_TOLERANCE * 100:.0f}%, "
            f"no roaster with >={_MIN_ROASTER_INSTOCK_FOR_WIPEOUT} in-stock beans wiped to 0"
        ),
        message=("; ".join(failing) if failing else "In-stock distribution within tolerance of snapshot."),
    )


def _check_batch_health(con, batch_results_path: Path) -> _CheckResult:
    """H. The last scraping batch must not have mostly failed. This is the
    gate between scraper errors and promotion: after an outage the rw DB
    holds stale/partial data and must not reach production."""
    def _skip(message: str, actual: str) -> _CheckResult:
        return _CheckResult(
            category="H. Batch health",
            name="last_batch_failure_rate",
            passed=True,
            actual=actual,
            threshold=f"failed<{_MAX_BATCH_FAILURE_FRACTION * 100:.0f}% of batch, beans_found>0",
            message=message,
        )

    if not batch_results_path.exists():
        return _skip("No batch results file found; skipping batch-health gate.", actual="no file")

    try:
        data = json.loads(batch_results_path.read_text(encoding="utf-8"))
        finished_at = datetime.fromisoformat(data["finished_at"])
        age_hours = (datetime.now(timezone.utc) - finished_at).total_seconds() / 3600
    except (json.JSONDecodeError, OSError, KeyError, ValueError, TypeError) as exc:
        return _skip(f"Batch results unreadable ({exc}); skipping gate.", actual="unreadable")

    total = int(data.get("total_scrapers", 0) or 0)
    failed = int(data.get("failed_count", 0) or 0)
    beans_total = sum(int(s.get("beans_found", 0) or 0) for s in data.get("scrapers", []))
    actual = f"failed={failed}/{total}, beans_found={beans_total:,}, age={age_hours:.1f}h"

    if age_hours > _BATCH_RESULTS_MAX_AGE_HOURS:
        return _skip(
            f"Batch results are {age_hours:.0f}h old (> {_BATCH_RESULTS_MAX_AGE_HOURS}h); skipping gate.",
            actual=actual,
        )

    failing: list[str] = []
    if total > 0 and failed / total >= _MAX_BATCH_FAILURE_FRACTION:
        failing.append(f"{failed}/{total} scrapers failed in the last batch")
    if beans_total == 0:
        failing.append("last batch found 0 beans across all scrapers")

    passed = not failing
    return _CheckResult(
        category="H. Batch health",
        name="last_batch_failure_rate",
        passed=passed,
        actual=actual,
        threshold=f"failed<{_MAX_BATCH_FAILURE_FRACTION * 100:.0f}% of batch, beans_found>0",
        message=(
            "; ".join(failing) + " — do not promote."
            if failing
            else "Last batch healthy."
        ),
    )


@app.command()
def validate_db(
    db_path: Path = typer.Option(
        _DEFAULT_DB_PATH,
        "--db-path",
        help="DuckDB file to validate. Defaults to data/rw_kissaten.duckdb.",
    ),
    snapshot_path: Path = typer.Option(
        _DEFAULT_SNAPSHOT_PATH,
        "--snapshot",
        help="JSON file with last-known-good row counts for drift comparison.",
    ),
    batch_results_path: Path = typer.Option(
        _DEFAULT_BATCH_RESULTS_PATH,
        "--batch-results",
        help="JSON file with the last scraping batch's per-scraper outcomes.",
    ),
    update_snapshot: bool = typer.Option(
        False,
        "--update-snapshot",
        help="If all checks pass, overwrite the snapshot with current counts.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
):
    """Run data validation checks against a DuckDB file before promoting it.

    Eight categories of checks are run, each wrapped in its own logfire span:

    A. Volume drift        — table row counts vs. last-known-good snapshot (±2 %)
    B. Required fields     — name, roaster, url, scraped_at, in_stock non-null
    C. Referential integ.  — beans↔roasters and beans↔origins links intact
    D. Normalization       — price→price_usd, currency_rates coverage
    E. Freshness           — at least one bean scraped in the last 24 h
    F. FTS index           — source within 200 rows of beans, index artifacts
                             (fts_main.docs / .terms) populated, match_bm25
                             returns at least one hit for a probe term
    G. In-stock drift      — global/per-roaster in-stock counts vs snapshot
    H. Batch health        — last scraping batch did not mostly fail

    Exits 0 if all checks pass, 1 if any fail. With --update-snapshot the
    snapshot is rewritten only if all checks pass, so the next run has a
    fresh baseline.

    Examples:
        kissaten validate-db                              # Validate the default rw DB
        kissaten validate-db --db-path data/custom.duckdb  # Validate another file
        kissaten validate-db --update-snapshot            # Refresh the baseline
    """
    setup_logging(verbose)

    with logfire.span(
        "validate_db",
        db_path=str(db_path),
        snapshot_path=str(snapshot_path),
        update_snapshot=update_snapshot,
        _tags=["validate_db"],
    ):
        if not db_path.exists():
            console.print(f"[red]Error: Database file not found: {db_path}[/red]")
            logfire.error(
                "validate_db target not found",
                db_path=str(db_path),
                _tags=["validate_db", "db_not_found"],
            )
            raise typer.Exit(1)

        snapshot = _load_snapshot(snapshot_path)
        if snapshot is None:
            console.print(
                f"[yellow]No snapshot found at {snapshot_path}; A/G checks will pass "
                f"without a baseline. Run with --update-snapshot after this to seed it.[/yellow]"
            )

        # Run each check inside its own span so failures are easy to spot in
        # the logfire trace UI. Order matches the docstring categories.
        results: list[_CheckResult] = []
        check_runners = [
            ("A. Volume drift", _check_volume_drift, (snapshot,)),
            ("B. Required fields", _check_required_fields, ()),
            ("C. Referential integrity", _check_referential_integrity, ()),
            ("D. Normalization", _check_normalization_invariants, ()),
            ("E. Freshness", _check_freshness, ()),
            ("F. FTS index", _check_fts_index, ()),
            ("F. FTS index", _check_fts_index_tables, ()),
            ("F. FTS index", _check_fts_match_probe, ()),
            ("G. In-stock drift", _check_instock_drift, (snapshot,)),
            ("H. Batch health", _check_batch_health, (batch_results_path,)),
        ]

        try:
            con = duckdb.connect(str(db_path), read_only=True)
        except Exception as exc:
            console.print(f"[red]Error opening {db_path}: {exc}[/red]")
            logfire.error(
                "validate_db failed to open database",
                db_path=str(db_path),
                error_message=str(exc),
                error_type=type(exc).__name__,
                _tags=["validate_db", "open_failed"],
            )
            raise typer.Exit(1)

        try:
            for category, runner, extra_args in check_runners:
                check_name = runner.__name__.removeprefix("_check_")
                with logfire.span(
                    "validate_db_check",
                    category=category,
                    check=check_name,
                    _tags=["validate_db", "check"],
                ):
                    try:
                        result = runner(con, *extra_args)
                    except Exception as exc:
                        result = _CheckResult(
                            category=category,
                            name=check_name,
                            passed=False,
                            actual="error",
                            threshold="check ran without error",
                            message=f"Check raised {type(exc).__name__}: {exc}",
                        )
                        logfire.exception(
                            "validate_db check raised an exception",
                            category=category,
                            check=check_name,
                            error_message=str(exc),
                            _tags=["validate_db", "check_exception"],
                        )
                    if result.passed:
                        logfire.info(
                            "validate_db check passed",
                            **result.to_logfire_dict(),
                            _tags=["validate_db", "check_passed"],
                        )
                    else:
                        logfire.error(
                            "validate_db check failed",
                            **result.to_logfire_dict(),
                            _tags=["validate_db", "check_failed"],
                        )
                    results.append(result)
        finally:
            con.close()

        # Console output: a single Rich table summarising all checks.
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Category", style="cyan")
        table.add_column("Check", style="white")
        table.add_column("Status", style="bold")
        table.add_column("Actual", style="green")
        table.add_column("Threshold", style="yellow")
        table.add_column("Message", style="dim")

        passed_count = 0
        failed_count = 0
        for r in results:
            status = "[green]PASS[/green]" if r.passed else "[red]FAIL[/red]"
            if r.passed:
                passed_count += 1
            else:
                failed_count += 1
            table.add_row(r.category, r.name, status, r.actual, r.threshold, r.message)

        console.print(table)

        all_passed = failed_count == 0
        logfire.info(
            "validate_db summary",
            total_checks=len(results),
            passed=passed_count,
            failed=failed_count,
            all_passed=all_passed,
            db_path=str(db_path),
            _tags=["validate_db", "summary"],
        )

        if all_passed:
            console.print(f"\n[bold green]✅ All {passed_count}/{len(results)} checks passed.[/bold green]")
            if update_snapshot:
                # Re-run the A check inline to capture the same counts it just
                # measured, then persist them. We do this here (not inside the
                # check function) so the snapshot is only written on success.
                with duckdb.connect(str(db_path), read_only=True) as scon:
                    new_counts = {
                        "coffee_beans": _query_scalar(scon, "SELECT COUNT(*) FROM coffee_beans"),
                        "origins": _query_scalar(scon, "SELECT COUNT(*) FROM origins"),
                        "roasters": _query_scalar(scon, "SELECT COUNT(DISTINCT roaster) FROM coffee_beans"),
                        "processed_files": _query_scalar(scon, "SELECT COUNT(*) FROM processed_files"),
                        "currencies_in_beans": _query_scalar(
                            scon, "SELECT COUNT(DISTINCT currency) FROM coffee_beans WHERE currency IS NOT NULL"
                        ),
                        "currency_rates_rows": _query_scalar(scon, "SELECT COUNT(*) FROM currency_rates"),
                        "in_stock_beans": _query_scalar(
                            scon, "SELECT COUNT(*) FROM coffee_beans WHERE in_stock = true"
                        ),
                        "in_stock_by_roaster": {
                            row[0]: int(row[1])
                            for row in scon.execute(
                                "SELECT roaster, COUNT(*) FROM coffee_beans WHERE in_stock = true GROUP BY roaster"
                            ).fetchall()
                        },
                    }
                _save_snapshot(snapshot_path, new_counts)
                console.print(f"[green]Snapshot updated:[/green] {snapshot_path}")
                logfire.info(
                    "validate_db snapshot updated",
                    snapshot_path=str(snapshot_path),
                    counts=new_counts,
                    _tags=["validate_db", "snapshot_updated"],
                )
            return
        else:
            console.print(
                f"\n[bold red]❌ {failed_count}/{len(results)} checks failed. "
                f"Do not promote {db_path.name} to production.[/bold red]"
            )
            raise typer.Exit(1)


@app.command()
def cache_stats(
    cache_db: Path = typer.Option(
        Path("data/ai_search_cache.duckdb"), "--cache-db", help="Path to the AI search cache database"
    ),
):
    """Display AI search cache statistics."""
    setup_logging(verbose=False)

    try:
        from kissaten.cache.ai_search_cache import AISearchCache

        cache = AISearchCache(cache_db)
        stats = cache.get_cache_stats()

        console.print("\n[bold cyan]🔍 AI Search Cache Statistics[/bold cyan]\n")

        # Overall stats
        table = Table(title="Cache Overview", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green", justify="right")

        table.add_row("Total Cached Queries", str(stats.get("total_cached_queries", 0)))
        table.add_row("Total Cache Hits", str(stats.get("total_hits", 0)))
        table.add_row("Cache Hit Rate", f"{stats.get('hit_rate', 0) * 100:.1f}%")
        table.add_row("Expired Entries", str(stats.get("expired_count", 0)))

        console.print(table)

        # Breakdown by type
        by_type = stats.get("by_type", {})
        if by_type:
            console.print("\n[bold]Queries by Type:[/bold]")
            type_table = Table(show_header=True)
            type_table.add_column("Type", style="cyan")
            type_table.add_column("Count", style="green", justify="right")

            for query_type, count in by_type.items():
                type_table.add_row(query_type.capitalize(), str(count))

            console.print(type_table)

        # Top queries
        top_queries = stats.get("top_queries", [])
        if top_queries:
            console.print("\n[bold]Top 10 Most Popular Queries:[/bold]")
            top_table = Table(show_header=True)
            top_table.add_column("Query", style="cyan", max_width=60)
            top_table.add_column("Type", style="yellow", max_width=10)
            top_table.add_column("Hits", style="green", justify="right")

            for query_info in top_queries:
                query_text = query_info["query"] or "(Image Query)"
                top_table.add_row(
                    query_text[:60] + "..." if len(query_text) > 60 else query_text,
                    query_info["type"],
                    str(query_info["hits"]),
                )

            console.print(top_table)

        console.print(f"\n[dim]Cache database: {cache_db}[/dim]")
        cache.close()

    except Exception as e:
        console.print(f"[red]Error retrieving cache statistics: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def cache_cleanup(
    cache_db: Path = typer.Option(
        Path("data/ai_search_cache.duckdb"), "--cache-db", help="Path to the AI search cache database"
    ),
):
    """Count expired cache entries (entries are preserved for dataset building)."""
    setup_logging(verbose=False)

    try:
        from kissaten.cache.ai_search_cache import AISearchCache

        cache = AISearchCache(cache_db)
        expired_count = cache.cleanup_expired()

        if expired_count > 0:
            console.print(
                f"[yellow]Found {expired_count} expired cache entries[/yellow]\n"
                f"[dim]Note: Expired entries are preserved for dataset building.[/dim]\n"
                f"[dim]Use 'kissaten cache-clear' to actually delete entries.[/dim]"
            )
        else:
            console.print("[dim]No expired entries found[/dim]")

        cache.close()

    except Exception as e:
        console.print(f"[red]Error checking cache: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def cache_clear(
    cache_db: Path = typer.Option(
        Path("data/ai_search_cache.duckdb"), "--cache-db", help="Path to the AI search cache database"
    ),
    query_type: str = typer.Option(
        None, "--type", help="Only clear specific type: 'text' or 'image' (clears all if not specified)"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
):
    """Clear all or specific cache entries."""
    setup_logging(verbose=False)

    if query_type and query_type not in ["text", "image"]:
        console.print("[red]Error: --type must be 'text' or 'image'[/red]")
        raise typer.Exit(1)

    # Confirmation prompt
    if not force:
        type_msg = f" ({query_type})" if query_type else ""
        if not typer.confirm(f"Are you sure you want to clear all{type_msg} cache entries?"):
            console.print("[dim]Operation cancelled[/dim]")
            return

    try:
        from kissaten.cache.ai_search_cache import AISearchCache

        cache = AISearchCache(cache_db)
        deleted_count = cache.clear_cache(query_type)

        type_msg = f" {query_type}" if query_type else ""
        console.print(f"[green]✓ Cleared {deleted_count}{type_msg} cache entries[/green]")

        cache.close()

    except Exception as e:
        console.print(f"[red]Error clearing cache: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def deduplicate_regions(
    country_code: str | None = typer.Argument(
        None,
        help="Two-letter ISO 3166-1 alpha-2 country code (e.g., PA for Panama, CO for Colombia). If not provided, processes all countries.",
    ),
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        help="Google API key for Gemini. If not provided, uses GOOGLE_API_KEY environment variable",
    ),
    opencage_key: str | None = typer.Option(
        None,
        "--opencage-key",
        help="OpenCage API key. If not provided, uses OPENCAGE_API_KEY environment variable",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview changes without creating mapping file",
    ),
    batch_size: int = typer.Option(
        10,
        "--batch-size",
        help="Number of regions to process before pausing (for rate limiting)",
    ),
    min_beans: int = typer.Option(
        1,
        "--min-beans",
        help="Only process regions with at least this many beans",
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        "-i",
        help="Allow manual selection of geocoding results when confidence is low or AI fails",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
):
    """
    Deduplicate regions using OpenCage geocoding and Gemini Flash AI.

    This command:
    1. Fetches all distinct regions for a country (or all countries)
    2. Geocodes each region using OpenCage API
    3. Uses Gemini Flash to select the best result from multiple matches
    4. Creates a JSON mapping file with canonical state names
    5. Stores full geocoding data for audit/debugging

    Example:
        kissaten deduplicate-regions             # Process all countries
        kissaten deduplicate-regions PA --dry-run  # Process only Panama
        kissaten deduplicate-regions CO --min-beans 5 --batch-size 20

    Rate Limits:
    - OpenCage free tier: 2,500 requests/day, ~1 req/sec
    - Gemini Flash: Generous free tier
    - Command auto-throttles to 1.5s between regions
    """
    setup_logging(verbose)

    import sys
    from pathlib import Path

    # Add project root to path to import from scripts/
    project_root = Path(__file__).parent.parent.parent.parent
    sys.path.insert(0, str(project_root))

    from scripts.deduplicate_regions import deduplicate_regions as run_deduplication
    from kissaten.api.db import conn

    async def process_all_countries():
        """Process all countries in the database."""
        countries_query = """
            SELECT DISTINCT country, COUNT(DISTINCT region) as region_count
            FROM origins
            WHERE country IS NOT NULL AND country != ''
              AND region IS NOT NULL AND region != ''
            GROUP BY country
            ORDER BY region_count DESC
        """
        countries = conn.execute(countries_query).fetchall()

        console.print(f"\n[bold blue]{'=' * 60}[/bold blue]")
        console.print(f"[bold blue]Found {len(countries)} countries to process[/bold blue]")
        console.print(f"[bold blue]{'=' * 60}[/bold blue]\n")

        all_stats = {}
        for idx, (cc, region_count) in enumerate(countries, 1):
            console.print(f"\n[bold cyan]{'=' * 60}[/bold cyan]")
            console.print(f"[bold cyan]Country {idx}/{len(countries)}: {cc} ({region_count} regions)[/bold cyan]")
            console.print(f"[bold cyan]{'=' * 60}[/bold cyan]\n")

            stats = await run_deduplication(
                country_code=cc,
                api_key=api_key,
                opencage_key=opencage_key,
                dry_run=dry_run,
                batch_size=batch_size,
                min_beans=min_beans,
                interactive=interactive,
            )
            all_stats[cc] = stats

        # Print overall summary
        console.print(f"\n[bold green]{'=' * 60}[/bold green]")
        console.print("[bold green]Overall Summary - All Countries[/bold green]")
        console.print(f"[bold green]{'=' * 60}[/bold green]\n")

        summary_table = Table(show_header=True, header_style="bold magenta")
        summary_table.add_column("Country", style="cyan")
        summary_table.add_column("Regions", justify="right", style="yellow")
        summary_table.add_column("Success", justify="right", style="green")
        summary_table.add_column("Failed", justify="right", style="red")
        summary_table.add_column("Invalid", justify="right", style="red")

        for cc, stats in all_stats.items():
            summary_table.add_row(
                cc,
                str(stats["total"]),
                str(stats["success"]),
                str(stats["failed"]),
                str(stats["invalid"]),
            )

        console.print(summary_table)
        console.print(f"\n[bold green]✓ All countries processed![/bold green]")

    if country_code:
        # Process single country
        asyncio.run(
            run_deduplication(
                country_code=country_code,
                api_key=api_key,
                opencage_key=opencage_key,
                dry_run=dry_run,
                batch_size=batch_size,
                min_beans=min_beans,
                interactive=interactive,
            )
        )
    else:
        # Process all countries
        asyncio.run(process_all_countries())


# --- Categorization Commands ---

categorize_app = typer.Typer(help="Categorize coffee data (processing, varietals, tasting notes)")
app.add_typer(categorize_app, name="categorize")


@categorize_app.command(name="processing")
def categorize_processing(
    review_and_merge: bool = typer.Option(
        False, "--review-and-merge", help="Run the review and merge phase after categorization"
    ),
    skip_validation: bool = typer.Option(
        False,
        "--skip-validation",
        help="Skip the post-categorization validation gate (not recommended).",
    ),
    database_path: Path = typer.Option(
        Path(__file__).parent.parent.parent.parent / "data/kissaten.duckdb",
        "--database-path",
        help="Path to the DuckDB database file",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
):
    """Categorize coffee processing methods."""
    setup_logging(verbose)
    from ..ai.processing_method_categorizer import ProcessCategorizer
    from ..ai.validation_gate import validate_processing_mappings_file

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

    # Post-categorization validation gate: catch any duplicate original_name
    # entries the LLM/merge step may have introduced before they poison the DB.
    if not skip_validation:
        validate_processing_mappings_file(categorizer.mappings_file)


@categorize_app.command(name="varietals")
def categorize_varietals(
    review_and_merge: bool = typer.Option(
        False, "--review-and-merge", help="Run the review and merge phase after categorization"
    ),
    retry_low_confidence: bool = typer.Option(
        True, "--retry/--no-retry", help="Retry mappings with confidence < 0.6 (e.g. previous errors)"
    ),
    skip_validation: bool = typer.Option(
        False,
        "--skip-validation",
        help="Skip the post-categorization validation gate (not recommended).",
    ),
    database_path: Path = typer.Option(
        Path(__file__).parent.parent.parent.parent / "data/kissaten.duckdb",
        "--database-path",
        help="Path to the DuckDB database file",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
):
    """Categorize coffee varietals using AI."""
    setup_logging(verbose)
    from ..ai.varietal_categorizer import VarietalCategorizer
    from ..ai.validation_gate import validate_varietal_mappings_file

    # Create the categorizer here so we can reach its mappings_file for the
    # post-run validation gate without refactoring the async run() helper.
    categorizer = VarietalCategorizer(database_path)

    async def run():
        threshold = 0.6 if retry_low_confidence else 0.0
        console.print("[bold cyan]Starting coffee varietal categorization...[/bold cyan]")
        await categorizer.categorize_all_varietals(min_confidence_threshold=threshold)
        if review_and_merge:
            console.print("\n[bold cyan]Reviewing canonical names for additional merges...[/bold cyan]")
            await categorizer.review_and_merge_canonical_names()
            console.print("[green]🔄 Review complete![/green]")

    asyncio.run(run())

    # Post-categorization validation gate: catch any duplicate original_name
    # entries the LLM/merge step may have introduced before they poison the DB.
    if not skip_validation:
        validate_varietal_mappings_file(categorizer.mappings_file)


@categorize_app.command(name="tasting-notes")
def categorize_tasting_notes(
    update_missing: bool = typer.Option(
        False, "--update-missing", help="Re-categorize existing notes that are missing a tertiary category."
    ),
    cleanup: bool = typer.Option(
        False,
        "--cleanup",
        help="Remove tasting notes from the CSV that are no longer present in the database.",
    ),
    recategorize_other: bool = typer.Option(
        False,
        "--recategorize-other",
        help=(
            "Re-process all 'Other' category notes: genuine flavours are re-categorized into "
            "proper categories; non-flavours (names, codes, errors) are marked as None."
        ),
    ),
    database_path: Path = typer.Option(
        Path(__file__).parent.parent.parent.parent / "data/kissaten.duckdb",
        "--database-path",
        help="Path to the DuckDB database file",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
):
    """Categorize coffee tasting notes and update taste lexicon."""
    setup_logging(verbose)
    from ..ai.tasting_note_categorizer import TastingNoteCategorizer

    # Paths for internal database files
    categorized_csv_path = Path(__file__).parent.parent / "database/tasting_notes_categorized.csv"
    taste_lexicon_path = Path(__file__).parent.parent / "database/taste_lexicon.json"

    async def run():
        categorizer = TastingNoteCategorizer(database_path, taste_lexicon_path, categorized_csv_path)

        if cleanup:
            stale_notes = categorizer.get_stale_notes()
            if stale_notes:
                console.print(
                    f"\n[yellow]Found {len(stale_notes)} tasting note(s) in the CSV that are no longer in the database:[/yellow]"
                )
                for note in stale_notes:
                    console.print(f"  [dim]- {note}[/dim]")
                if typer.confirm(f"\nDelete these {len(stale_notes)} stale note(s) from the CSV?"):
                    removed = categorizer.remove_stale_notes(stale_notes)
                    console.print(f"[green]✅ Removed {removed} stale note(s) from {categorized_csv_path}[/green]")
                else:
                    console.print("[dim]Skipped cleanup.[/dim]")
            else:
                console.print("[green]No stale notes found — CSV is already in sync with the database.[/green]")

        console.print("[bold cyan]Starting coffee tasting note categorization...[/bold cyan]")
        await categorizer.categorize_all_notes(batch_size=50, update_tertiary=update_missing)
        console.print(f"[green]✅ Categorization complete! Results saved to {categorized_csv_path}[/green]")

        if recategorize_other:
            console.print("\n[bold cyan]Re-processing 'Other' category notes...[/bold cyan]")
            non_flavour_count, recategorized_count = await categorizer.recategorize_other_notes(batch_size=50)
            console.print(
                f"[green]✅ 'Other' cleanup complete: [bold]{non_flavour_count}[/bold] non-flavours marked as None, "
                f"[bold]{recategorized_count}[/bold] notes re-categorized.[/green]"
            )

        console.print("\n[bold cyan]Updating lexicon with new potential tertiary categories...[/bold cyan]")
        await categorizer.update_lexicon_with_new_tertiary_categories(
            min_count=3,
            output_lexicon_path=taste_lexicon_path,
        )
        console.print("[green]🔄 Lexicon update complete![/green]")

    asyncio.run(run())


@categorize_app.command(name="all")
def categorize_all(
    review_and_merge: bool = typer.Option(False, "--review-and-merge", help="Run review/merge phase for all"),
    skip_validation: bool = typer.Option(
        False,
        "--skip-validation",
        help="Skip the post-categorization validation gates (not recommended).",
    ),
    database_path: Path = typer.Option(
        Path(__file__).parent.parent.parent.parent / "data/kissaten.duckdb",
        "--database-path",
        help="Path to the DuckDB database file",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
):
    """Run all categorization processes sequentially."""
    setup_logging(verbose)
    console.print("\n[bold magenta]🚀 Running ALL categorization tasks sequentially...[/bold magenta]\n")

    # Processing Methods
    console.print("[bold blue]Task 1/3: Processing Methods[/bold blue]")
    categorize_processing(
        review_and_merge=review_and_merge,
        skip_validation=skip_validation,
        database_path=database_path,
        verbose=verbose,
    )

    # Varietals
    console.print("\n[bold blue]Task 2/3: Varietals[/bold blue]")
    categorize_varietals(
        review_and_merge=review_and_merge,
        retry_low_confidence=True,
        skip_validation=skip_validation,
        database_path=database_path,
        verbose=verbose,
    )

    # Tasting Notes
    console.print("\n[bold blue]Task 3/3: Tasting Notes[/bold blue]")
    categorize_tasting_notes(
        update_missing=False, cleanup=False, recategorize_other=False, database_path=database_path, verbose=verbose
    )

    console.print("\n[bold green]✨ All categorization tasks completed successfully![/bold green]")


@app.command()
def validate_mappings(
    allow_redundant: bool = typer.Option(
        False,
        "--allow-redundant",
        help="Only fail on duplicates with conflicting canonicals/common_name; allow harmless duplicates that agree.",
    ),
):
    """Validate varietal and processing-method mappings for duplicate original_name entries.

    Exits with a non-zero status if any duplicate is found, making this command
    suitable for use as a CI check (e.g. ``kissaten validate-mappings``).
    """
    setup_logging(verbose=False)
    from ..ai.processing_method_categorizer import ProcessCategorizer
    from ..ai.varietal_categorizer import VarietalCategorizer

    base = Path(__file__).parent.parent / "database"
    varietal_file = base / "varietal_mappings.json"
    processing_file = base / "processing_methods_mappings.json"

    any_issues = False

    if varietal_file.exists():
        with open(varietal_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        issues = VarietalCategorizer.validate_mappings_static(data)
        if allow_redundant:
            issues = [i for i in issues if i["is_conflict"]]
        VarietalCategorizer.print_validation_report_static(issues, varietal_file)
        any_issues = any_issues or bool(issues)
    else:
        console.print(f"[yellow]Varietal mappings file not found: {varietal_file}[/yellow]")

    if processing_file.exists():
        with open(processing_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        issues = ProcessCategorizer.validate_mappings_static(data)
        if allow_redundant:
            issues = [i for i in issues if i["is_conflict"]]
        ProcessCategorizer.print_validation_report_static(issues, processing_file)
        any_issues = any_issues or bool(issues)
    else:
        console.print(f"[yellow]Processing methods mappings file not found: {processing_file}[/yellow]")

    if any_issues:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
