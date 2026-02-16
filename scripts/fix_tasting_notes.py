"""Script to fix long tasting notes in the database and JSON files."""

import asyncio
import json
import logging
from pathlib import Path

import dotenv
import duckdb
from rich.console import Console
from rich.progress import Progress

from kissaten.ai.tasting_note_splitter import TastingNoteSplitter
from kissaten.schemas.coffee_bean import CoffeeBean

# Load environment variables
dotenv.load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
console = Console()

def get_database_path():
    """Get the database path."""
    return Path(__file__).parent.parent / "data" / "rw_kissaten.duckdb"

async def fix_long_tasting_notes():
    """Find beans with long tasting notes and split them using AI."""
    db_path = get_database_path()
    if not db_path.exists():
        console.print(f"[red]Database not found at {db_path}[/red]")
        return

    conn = duckdb.connect(str(db_path))
    
    # Find beans with exactly one tasting note that is somewhat long
    # or contains common delimiters or sentence words
    query = """
        SELECT id, name, roaster, tasting_notes, filename
        FROM coffee_beans
        WHERE array_length(tasting_notes) = 1
        AND (
            length(tasting_notes[1]) > 15
            OR tasting_notes[1] LIKE '% / %'
            OR tasting_notes[1] LIKE '% - %'
            OR tasting_notes[1] LIKE '% & %'
            OR tasting_notes[1] LIKE '% with %'
            OR tasting_notes[1] LIKE '% and %'
            OR tasting_notes[1] LIKE '%, %'
            OR tasting_notes[1] LIKE '%. %'
        )
    """
    
    beans = conn.execute(query).fetchall()
    console.print(f"[cyan]Found {len(beans)} beans with potentially unsplit tasting notes.[/cyan]")

    if not beans:
        conn.close()
        return

    splitter = TastingNoteSplitter()
    data_dir = Path(__file__).parent.parent / "data"

    with Progress() as progress:
        task = progress.add_task("[green]Splitting notes...", total=len(beans))
        
        for bean_id, name, roaster, notes, filename in beans:
            original_note = notes[0]
            # 0. Check if JSON is already updated
            json_path = data_dir / filename
            if json_path.exists():
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    current_notes = data.get("tasting_notes", [])
                    if len(current_notes) > 1:
                        progress.update(task, advance=1)
                        continue
                except Exception as e:
                    progress.console.print(f"  [red]Error reading JSON: {e}[/red]")

            progress.console.print(f"Processing: [bold]{roaster} - {name}[/bold]")
            progress.console.print(f"  Note: {original_note[:70]}...")

            # Split using AI
            try:
                split_notes = await splitter.split_notes(original_note)
                progress.console.print(f"  Result: {split_notes}")

                if split_notes and split_notes != [original_note]:
                    # Update JSON file
                    json_path = data_dir / filename
                    if json_path.exists():
                        try:
                            with open(json_path, "r", encoding="utf-8") as f:
                                data = json.load(f)
                            
                            data["tasting_notes"] = split_notes
                            
                            with open(json_path, "w", encoding="utf-8") as f:
                                json.dump(data, f, indent=2, ensure_ascii=False)
                            
                            progress.console.print(f"  [green]Updated JSON: {filename}[/green]")
                        except Exception as e:
                            progress.console.print(f"  [red]Error updating JSON: {e}[/red]")
                    else:
                        progress.console.print(f"  [yellow]JSON file not found: {filename}[/yellow]")
                else:
                    progress.console.print("  [yellow]No changes needed or AI returned same note.[/yellow]")

            except Exception as e:
                progress.console.print(f"  [red]Error processing {name}: {e}[/red]")
            
            progress.update(task, advance=1)
            # Small sleep to avoid aggressive rate limiting
            await asyncio.sleep(0.5)

    conn.commit()
    conn.close()
    console.print("[bold green]Done![/bold green]")

if __name__ == "__main__":
    asyncio.run(fix_long_tasting_notes())
