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

    conn = duckdb.connect(str(db_path), config={"enable_external_access": False})
    
    # Find beans with any tasting note that is somewhat long
    # or contains common delimiters or sentence words
    query = """
        SELECT id, name, roaster, tasting_notes, filename
        FROM coffee_beans
        WHERE EXISTS (
            SELECT 1 FROM unnest(tasting_notes) AS t(note)
            WHERE length(note) > 40
            OR note LIKE '% / %'
            OR note LIKE '% - %'
            OR note LIKE '% & %'
            OR note LIKE '% with %'
            OR note LIKE '% and %'
            OR note LIKE '%, %'
            OR note LIKE '%. %'
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
            progress.console.print(f"Processing: [bold]{roaster} - {name}[/bold]")
            
            # 0. Check if JSON needs update
            json_path = data_dir / filename
            if not json_path.exists():
                logger.warning(f"JSON file not found: {filename}")
                progress.update(task, advance=1)
                continue

            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    current_data = json.load(f)
                
                # We'll use the notes from the database as the source of truth for checking,
                # but update the JSON file contents.
                all_new_notes = []
                changed = False
                
                for note in notes:
                    # Decide if this specific note needs splitting
                    needs_splitting = (
                        len(note) > 15
                        or " / " in note
                        or " - " in note
                        or " & " in note
                        or " with " in note.lower()
                        or " and " in note.lower()
                        or ", " in note
                        or ". " in note
                    )
                    
                    if needs_splitting:
                        split_result = await splitter.split_notes(note)
                        if split_result and split_result != [note]:
                            all_new_notes.extend(split_result)
                            changed = True
                        else:
                            all_new_notes.append(note)
                    else:
                        all_new_notes.append(note)

                if changed:
                    # Deduplicate while preserving order
                    seen = set()
                    final_notes = []
                    for n in all_new_notes:
                        if n not in seen:
                            final_notes.append(n)
                            seen.add(n)
                    
                    current_data["tasting_notes"] = final_notes
                    
                    with open(json_path, "w", encoding="utf-8") as f:
                        json.dump(current_data, f, indent=2, ensure_ascii=False)
                    
                    progress.console.print(f"  [green]Updated JSON: {filename}[/green]")
                    progress.console.print(f"  [cyan]Before:[/cyan] {notes}")
                    progress.console.print(f"  [green]After: [/green] {final_notes}")
                else:
                    progress.console.print("  [yellow]No changes needed or AI returned same notes.[/yellow]")

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
