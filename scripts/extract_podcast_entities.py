# /// script
# dependencies = ["pydantic-ai", "pydantic", "python-dotenv", "rich"]
# requires-python = ">=3.10"
# ///

"""Extract coffee-domain entities from podcast episode titles + descriptions with Gemini Flash-Lite.

The output is meant to seed ASR word-boosting hotwords, so we deliberately store the
*surface form* exactly as it appeared in the text and do NOT attempt canonical-ID
resolution (the farm/varietal mapping files are incomplete, e.g. farm_mappings.json
is Colombia-only).

Writes `podcast_data/<podcast>/<slug>.entities.json` next to each `.metadata.json`.

Usage:
    uv run scripts/extract_podcast_entities.py
    uv run scripts/extract_podcast_entities.py --force
    uv run scripts/extract_podcast_entities.py --episode <path/to/x.metadata.json>
"""

import argparse
import asyncio
import json
import logging
import re
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModelSettings
from rich.console import Console
from rich.progress import Progress

load_dotenv()

console = Console()
logger = logging.getLogger(__name__)

PODCAST_DATA_DIR = Path(__file__).parent.parent / "podcast_data"

# pydantic-ai 2.51.0 rejects the legacy `google-gla:` prefix in `Agent(...)`
# ("Unknown model: google-gla:... Did you mean 'google:...'?"), so use `google:`,
# which is what the rest of the repo uses (ai/extractor.py, ai/region_selector.py,
# ai/search_agent.py).
MODEL = "google:gemini-2.5-flash-lite"
MAX_RETRIES = 3

# The prompt asks the model to skip sponsor/production credits, but flash-lite still leaks
# them occasionally. These names recur in nearly every description as pure boilerplate, so
# drop them deterministically - a false hotword actively hurts ASR recognition.
DROP_ENTITIES = {
    "nick hafner",  # cover artist credit
    "elijah bisbee",  # intro song credit
    "patreon",
    "paypal",
    "buzzsprout",
    "luxiacoffee",  # host's own store, self-promo
    "ventolacoffee",
    "unblendedcoffee",
}

SYSTEM_PROMPT = """
You are a specialty-coffee domain extractor. You are given the TITLE and DESCRIPTION of a
podcast episode. Extract only entities that are genuinely *discussed as the subject matter
of the episode*, and return each one exactly as it is written in the text.

Extract these five categories:
- persons: named people who are guests, producers, farmers, hosts, or researchers being discussed.
- farms: named farms, estates, cooperatives, wet mills, washing stations, or producer organisations.
- locations: named countries, regions, cities, or coffee-producing areas.
- processes: processing methods and fermentation techniques (Washed, Natural, Honey, Anaerobic, etc.).
- varietals: coffee cultivars and species (Typica, Gesha, Bourbon, Arabica, Robusta, Caturra, etc.).

CRITICAL - IGNORE SPONSOR AND BOILERPLATE. Episode descriptions are padded with promotional
housekeeping that has nothing to do with the topic. Never extract anything from these:
- sponsor / advertiser / roaster names read at the end of the show
- Patreon, Patreon tiers, Discord perks, PayPal donation links, newsletter plugs, merch
- tracking / shortened URLs, social-media handles, "Mentioned in the Episode" link lists
- "Cover Art by: ..." and "Intro song:" / "Into song:" credits. Nick Hafner (cover artist) and
  Elijah Bisbee (intro song) are production credits, NEVER episode guests - do not put them
  in `persons` even though they are the only capitalised names left in the text.
- "Support the show", "Resources:" blocks that are purely support/promo links
- the podcast network name and generic platform names (Buzzsprout, Spotify, Apple Podcasts)

The test for every candidate: would this name be spoken during the actual conversation about
coffee? A farm that is the *subject* of the conversation counts. A roaster that is merely
sponsored does not. Producer / farm / importer credit lists (e.g. "Producers I work with:
Ana - Finca Esperanza, Guatemala") DO count: those are real coffee-domain entities even though
they sit in the resources block.

Also:
- If a category has nothing relevant, return an empty list for it. Returning nothing is ALWAYS
  better than guessing or padding a list. Do not invent plausible-sounding coffee names.
- Keep the surface spelling from the text. Do not translate, expand acronyms, or "correct" spellings.
- Deduplicate case-insensitively, but keep the first spelling you saw.
- Do not include the episode's own podcast host unless the episode is genuinely about them.

FINAL CHECK before you answer. Re-read your `persons` list and delete anything that comes from a
credit, promo, sponsor or support line rather than from the conversation. If deleting those leaves
`persons` empty, that is the correct answer - an empty list is right and a sponsor name is wrong.

Also write a `summary`: ONE sentence, max ~200 characters, describing what the episode is about.
No trailing period needed. If the description is pure boilerplate, summarise the topic from the title.
"""


class EpisodeEntities(BaseModel):
    """Coffee-domain entities for one episode, stored as surface forms."""

    episode_id: str = Field(..., description="Episode slug derived from the metadata filename")
    persons: list[str] = Field(default_factory=list, description="Named people discussed in the episode")
    farms: list[str] = Field(default_factory=list, description="Named farms, estates, co-ops, wet mills")
    locations: list[str] = Field(default_factory=list, description="Countries, regions, cities")
    processes: list[str] = Field(default_factory=list, description="Processing / fermentation methods")
    varietals: list[str] = Field(default_factory=list, description="Coffee cultivars and species")
    summary: str = Field(default="", description="One sentence (<=200 chars) on what the episode is about")


_agent: Agent[EpisodeEntities, EpisodeEntities] | None = None


def get_agent() -> Agent[EpisodeEntities, EpisodeEntities]:
    global _agent
    if _agent is None:
        _agent = Agent(
            MODEL,
            output_type=EpisodeEntities,
            system_prompt=SYSTEM_PROMPT,
            model_settings=GoogleModelSettings(google_thinking_config={"thinking_budget": 0}),
        )
    return _agent


def dedupe(values: list[str]) -> list[str]:
    """Case-insensitive dedupe preserving first-seen order, dropping empties and boilerplate."""
    seen: set[str] = set()
    out: list[str] = []
    for v in values:
        v = v.strip()
        if not v:
            continue
        key = v.lower()
        if key in DROP_ENTITIES:
            logger.debug(f"dropping boilerplate entity: {v}")
            continue
        if key not in seen:
            seen.add(key)
            out.append(v)
    return out


async def extract_episode(metadata_path: Path) -> EpisodeEntities:
    """Call the model for one episode and return validated entities."""
    with open(metadata_path) as f:
        meta = json.load(f)

    episode_id = metadata_path.name[: -len(".metadata.json")]
    title = (meta.get("episode_title") or "").strip()
    description = (meta.get("description") or "").strip()

    prompt = f"TITLE:\n{title}\n\nDESCRIPTION:\n{description or '(none)'}\n"

    agent = get_agent()
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = await agent.run(prompt)
            out = result.output
            out.episode_id = episode_id
            out.persons = dedupe(out.persons)
            out.farms = dedupe(out.farms)
            out.locations = dedupe(out.locations)
            out.processes = dedupe(out.processes)
            out.varietals = dedupe(out.varietals)
            out.summary = re.sub(r"\s+", " ", out.summary).strip()[:200]
            return out
        except Exception as e:  # noqa: BLE001 - per-episode isolation is the point
            last_error = e
            logger.warning(f"attempt {attempt}/{MAX_RETRIES} failed for {episode_id}: {e}")
            await asyncio.sleep(2 * attempt)

    raise RuntimeError(f"{episode_id}: {last_error}")


def output_path_for(metadata_path: Path) -> Path:
    return metadata_path.with_name(metadata_path.name[: -len(".metadata.json")] + ".entities.json")


async def process_one(metadata_path: Path, force: bool) -> tuple[str, str]:
    """Returns (outcome, error_message) where outcome is 'processed' | 'skipped' | 'failed'."""
    out_path = output_path_for(metadata_path)
    if out_path.exists() and not force:
        return "skipped", ""

    try:
        entities = await extract_episode(metadata_path)
    except Exception as e:  # noqa: BLE001 - keep going, report at the end
        logger.error(f"FAILED {metadata_path.parent.name}/{metadata_path.name}: {e}")
        return "failed", f"{type(e).__name__}: {e}"

    out_path.write_text(entities.model_dump_json(indent=2))
    return "processed", ""


async def process_all(force: bool = False, only: Path | None = None) -> int:
    if only is not None:
        files = [only]
    else:
        files = sorted(PODCAST_DATA_DIR.glob("*/*.metadata.json"))

    console.print(f"Model: {MODEL}")
    console.print(f"Found {len(files)} metadata files")

    processed = skipped = failed = 0
    failures: list[tuple[str, str]] = []

    with Progress(console=console) as progress:
        task = progress.add_task("Extracting entities...", total=len(files))
        for path in files:
            outcome, e_msg = await process_one(path, force)
            if outcome == "processed":
                processed += 1
            elif outcome == "skipped":
                skipped += 1
            else:
                failed += 1
                failures.append((f"{path.parent.name}/{path.name}", e_msg))
            progress.update(task, advance=1)

    console.print(f"\nDone: {processed} processed, {skipped} skipped, {failed} failed")
    for name, msg in failures:
        console.print(f"  [red]FAILED[/red] {name}: {msg}")

    return 1 if failed else 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract coffee entities from podcast titles + descriptions")
    parser.add_argument("--force", action="store_true", help="Re-run over episodes that already have an entities file")
    parser.add_argument("--episode", type=str, help="Process a single .metadata.json file")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    only = Path(args.episode) if args.episode else None
    raise SystemExit(asyncio.run(process_all(force=args.force, only=only)))


if __name__ == "__main__":
    main()
