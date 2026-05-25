"""Batch process podcast transcripts and save analysis as JSON files.

Usage:
    uv run python scripts/ingest_podcasts.py                    # Process all unprocessed transcripts
    uv run python scripts/ingest_podcasts.py --force             # Reprocess all transcripts
    uv run python scripts/ingest_podcasts.py --episode path.json  # Process a single transcript
"""

import argparse
import asyncio
import logging
from pathlib import Path

from rich.console import Console
from rich.progress import Progress

console = Console()
logger = logging.getLogger(__name__)

PODCAST_DATA_DIR = Path(__file__).parent.parent / "podcast_data"


async def process_episode(transcript_path: Path, force: bool = False) -> bool:
    """Analyze a single episode and save the .analysis.json alongside the transcript.

    Returns True if processing was done, False if skipped.
    """
    from kissaten.ai.podcast_tagger import PodcastTagger

    output_path = transcript_path.with_suffix(".analysis.json")
    if output_path.exists() and not force:
        logger.info(f"Skipping {transcript_path.name} (analysis exists)")
        return False

    tagger = PodcastTagger()
    analysis = await tagger.analyze_episode(transcript_path)

    with open(output_path, "w") as f:
        f.write(analysis.model_dump_json(indent=2))
    logger.info(f"Saved analysis to {output_path}")
    return True


async def process_all(force: bool = False):
    """Process all podcast transcripts that don't have an analysis file yet."""
    # Find all .json files in the podcast_data directory, excluding .analysis.json and .metadata.json
    all_json_files = sorted(PODCAST_DATA_DIR.glob("**/*.json"))
    transcript_files = [
        f for f in all_json_files if not f.name.endswith(".analysis.json") and not f.name.endswith(".metadata.json")
    ]
    console.print(f"Found {len(transcript_files)} transcript files")

    processed = 0
    skipped = 0
    errors = 0

    with Progress(console=console) as progress:
        task = progress.add_task("Processing episodes...", total=len(transcript_files))
        for path in transcript_files:
            try:
                done = await process_episode(path, force=force)
                if done:
                    processed += 1
                else:
                    skipped += 1
            except Exception as e:
                logger.error(f"Error processing {path.name}: {e}")
                errors += 1
            progress.update(task, advance=1)

    console.print(f"\nDone: {processed} processed, {skipped} skipped, {errors} errors")


def main():
    parser = argparse.ArgumentParser(description="Batch process podcast transcripts")
    parser.add_argument("--force", action="store_true", help="Reprocess all transcripts")
    parser.add_argument("--episode", type=str, help="Process a single transcript file")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.episode:
        path = Path(args.episode)
        if not path.exists():
            console.print(f"[red]File not found: {path}[/red]")
            return
        asyncio.run(process_episode(path, force=args.force))
    else:
        asyncio.run(process_all(force=args.force))


if __name__ == "__main__":
    main()
