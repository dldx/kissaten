from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.gemini import GeminiModelSettings

load_dotenv()

logger = logging.getLogger(__name__)

class PodcastEntity(BaseModel):
    """Refined entity identified in a podcast segment."""
    entity_type: str = Field(..., description="One of: 'variety', 'farm', 'process', 'origin'")
    raw_name: str = Field(..., description="The name as mentioned in the transcript")
    canonical_id: str | None = Field(None, description="The resolved canonical ID from kissaten database")

class PodcastSegment(BaseModel):
    """A topical segment of a podcast episode."""
    title: str = Field(..., description="Catchy title for this segment")
    summary: str = Field(..., description="Short 1-2 sentence summary of what is discussed")
    timestamp_start: float | None = Field(None, description="Start time in seconds")
    timestamp_end: float | None = Field(None, description="End time in seconds")
    entities: list[PodcastEntity] = Field(default_factory=list, description="Coffee entities mentioned in this segment")
    key_takeaway: str | None = Field(None, description="The most interesting insight from this segment")
    raw_text: str | None = Field(
        None, description="Raw transcript text for this segment, populated by post-processing"
    )

class PodcastEpisodeAnalysis(BaseModel):
    """Complete analysis of a podcast episode."""
    id: str = Field(..., description="Unique episode ID derived from filename slug")
    podcast_name: str = Field(..., description="Name of the podcast series")
    episode_title: str
    url: str | None = Field(None, description="URL of the episode if known")
    segments: list[PodcastSegment]

class PodcastTagger:
    """Uses LLM to segment and tag podcast transcripts."""

    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not set")

        # Load mappings for reference in the prompt
        self.varieties = self._load_mapping("varietal_mappings.json")
        self.farms = self._load_mapping("farm_mappings.json")
        self.processes = self._load_mapping("processing_methods_mappings.json")

        self.agent = Agent(
            "gemini-3-flash-preview", # Using flash for cost/speed
            output_type=PodcastEpisodeAnalysis,
            system_prompt=self._get_system_prompt(),
            model_settings=GeminiModelSettings(gemini_thinking_config={"thinking_budget": 0}),
        )

    def _load_mapping(self, filename: str) -> list[str]:
        path = Path(__file__).parent.parent / "database" / filename
        if not path.exists():
            return []
        try:
            with open(path) as f:
                data = json.load(f)
                if isinstance(data, list):
                    # Extract unique canonical names for the LLM to use as reference
                    names = set()
                    for entry in data:
                        if "canonical_names" in entry:
                            names.update(entry["canonical_names"])
                        elif "canonical_farm_name" in entry:
                            names.add(entry["canonical_farm_name"])
                        elif "canonical_name" in entry:
                            names.add(entry["canonical_name"])
                    return sorted(list(names))
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
        return []

    def _get_system_prompt(self) -> str:
        variety_list = ", ".join(self.varieties[:200]) # Limit to avoid bloat
        process_list = ", ".join(self.processes[:100])

        return f"""
You are a specialty coffee expert and technical analyst.
Your task is to analyze a podcast transcript and divide it into meaningful topical segments.

The transcript is provided as timestamped chunks. Use the actual chunk timestamps to determine
the start and end times for each segment. Do NOT estimate or approximate timestamps.

For each segment:
1. Identify the topic (e.g., 'Alternative fermentation methods', 'History of Geisha in Panama').
2. Provide a concise summary.
3. Extract the start timestamp from the first relevant chunk and the end timestamp from the last
   relevant chunk.
4. Identify specific coffee entities mentioned BY NAME in the transcript.

Entity extraction rules:
- Extract entities that are discussed or referenced in the transcript. Do NOT invent abstract
  category labels (e.g., do NOT create 'Mixed Varieties', 'Unknown Cultivar', or 'Various Origins').
- If a segment discusses a topic generally without referencing any specific entity, leave entities empty.
- Entity types:
   - variety: Specific coffee cultivars (e.g., Sidra, SL28, Gesha, Pink Bourbon, Bourbon, Typica)
   - farm: Named farms, estates, cooperatives, or producer organizations
     (e.g., Finca Debora, The Coffee Gardens, Karagoto Cooperative)
   - process: Processing methods AND fermentation techniques discussed in the transcript.
     This includes traditional methods (e.g., Washed, Natural, Honey) as well as specific
     techniques (e.g., Yeast Inoculation, Anaerobic Fermentation, Submerged Fermentation,
     Carbonic Maceration, Thermal Shock). If a technique is a central topic of a segment,
     it MUST be extracted as a process entity.
     Use the canonical name from the PROCESSES reference list when possible.
   - origin: Named countries, regions, or specific geographic locations
     (e.g., Uganda, Mount Elgon, Huila, Nyeri)

Technical Note: If a name is misspelled in the transcript (e.g. 'Gaysha' or 'Sl 28'),
identify it correctly as the intended coffee entity.

REFERENCE LISTS (Use these as a guide for canonical names if possible):
VARIETIES: {variety_list}
PROCESSES: {process_list}
"""

    async def analyze_episode(self, transcript_path: Path) -> PodcastEpisodeAnalysis:
        with open(transcript_path) as f:
            data = json.load(f)

            # The files are JSON with 'text' and 'chunks'
            chunks = data.get("chunks", [])

        # Build a timestamped transcript for the LLM so it can use real timestamps
        timestamped_lines = []
        for chunk in chunks:
            text = chunk.get("text", "").strip()
            ts = chunk.get("timestamp", [0, 0])
            if text:
                start = ts[0] if len(ts) > 0 else 0
                timestamped_lines.append(f"[{start:.1f}s] {text}")

        timestamped_transcript = "\n".join(timestamped_lines)

        # Derive metadata from filesystem path
        # e.g. podcast_data/making-coffee-with-lucia-solis/episode.txt
        podcast_name = transcript_path.parent.name  # directory name = podcast slug
        episode_slug = transcript_path.stem  # filename without .txt

        prompt = (
            f"Analyze this podcast transcript.\n"
            f"id: {episode_slug}\n"
            f"podcast_name: {podcast_name}\n\n"
            f"Timestamped Transcript:\n{timestamped_transcript}"
        )

        try:
            result = await self.agent.run(prompt)
            analysis = result.output

            # Ensure metadata is set correctly (LLM may guess differently)
            analysis.id = episode_slug
            analysis.podcast_name = podcast_name

            # Post-process: populate raw_text on each segment from chunks
            self._fill_raw_text(analysis, chunks)

            await self._resolve_entities(analysis)
            return analysis
        except Exception as e:
            logger.error(f"Error analyzing episode {transcript_path}: {e}")
            raise

    def _fill_raw_text(self, analysis: PodcastEpisodeAnalysis, chunks: list):
        """Slice transcript chunks by segment timestamps to populate raw_text."""
        for segment in analysis.segments:
            if segment.timestamp_start is None or segment.timestamp_end is None:
                continue
            texts = []
            for chunk in chunks:
                text = chunk.get("text", "").strip()
                ts = chunk.get("timestamp", [0, 0])
                if not text or len(ts) < 2:
                    continue
                chunk_start = ts[0]
                chunk_end = ts[1]
                if chunk_start is None or chunk_end is None:
                    continue
                # Include chunk if it overlaps with the segment time range
                if chunk_end >= segment.timestamp_start and chunk_start < segment.timestamp_end:
                    texts.append(text)
            segment.raw_text = " ".join(texts)

    async def _resolve_entities(self, analysis: PodcastEpisodeAnalysis):
        """Fuzzy match extracted entities to canonical IDs."""
        # Selection logic will be handled by the ingestion script
        pass

async def main():
    import sys
    logging.basicConfig(level=logging.INFO)
    tagger = PodcastTagger()

    # Example usage: uv run python3 -m src.kissaten.ai.podcast_tagger podcast_data/path/to/file.txt
    if len(sys.argv) > 1:
        transcript_path = Path(sys.argv[1])
        if transcript_path.exists():
            analysis = await tagger.analyze_episode(transcript_path)
            # Save output as .analysis.json
            output_path = transcript_path.with_suffix(".analysis.json")
            with open(output_path, "w") as f:
                f.write(analysis.model_dump_json(indent=2))
            print(f"Analysis saved to {output_path}")

if __name__ == "__main__":
    asyncio.run(main())
