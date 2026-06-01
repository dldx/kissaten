from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.gemini import GeminiModelSettings

load_dotenv()

logger = logging.getLogger(__name__)

class PodcastEntity(BaseModel):
    """Refined entity identified in a podcast segment."""

    entity_type: str = Field(..., description="One of: 'variety', 'farm', 'process', 'origin', 'producer'")
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
    """Complete analysis of a podcast episode or media document."""
    id: str = Field(..., description="Unique episode ID derived from filename slug")
    podcast_name: str = Field(..., description="Name of the podcast series or blog")
    media_type: str = Field("podcast", description="Type of media (podcast, blog, video)")
    episode_title: str
    url: str | None = Field(None, description="URL of the episode if known")
    segments: list[PodcastSegment]

class PodcastExtraction(BaseModel):
    """Entities extracted from a single segment."""

    entities: list[PodcastEntity] = Field(default_factory=list)


class PodcastTagger:
    """Uses LLM to segment and tag podcast transcripts."""

    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not set")

        self.genai_client = genai.Client(api_key=self.api_key)

        # Build and setup context cache for the extractor
        self.cache_name = self._setup_cache()

        # Stage 1: Segmentation
        self.segmenter = Agent(
            "google-gla:gemini-3.5-flash",
            output_type=PodcastEpisodeAnalysis,
            system_prompt=self._get_segmenter_prompt(),
            model_settings=GeminiModelSettings(gemini_thinking_config={"thinking_budget": 0}),
        )

        # Stage 2: Entity Extraction (with Cache)
        self.extractor = Agent(
            "google-gla:gemini-3.5-flash",
            output_type=PodcastExtraction,
            system_prompt=self._get_extractor_prompt(),
            model_settings=GeminiModelSettings(
                gemini_thinking_config={"thinking_budget": 0}, cached_content=self.cache_name
            ),
        )

    def _setup_cache(self) -> str:
        """Builds the reference text and creates a Gemini context cache."""
        ref_text = self._build_reference_text()

        logger.info(f"Creating Gemini context cache (approx {len(ref_text) // 4} tokens)...")
        try:
            cache = self.genai_client.caches.create(
                model="models/gemini-3.5-flash",
                config=types.CreateCachedContentConfig(
                    display_name="Coffee Reference Library",
                    system_instruction=(
                        "You are a specialty coffee expert. Your goal is to extract coffee entities "
                        "and map them to the canonical IDs provided in the COFFEE REFERENCE LIBRARY "
                        "in your context. Use fuzzy matching and coffee knowledge to resolve "
                        "misspellings or informal names to their canonical IDs."
                    ),
                    contents=[ref_text],
                    ttl="3600s",
                ),
            )
            return cache.name
        except Exception as e:
            logger.error(f"Failed to create cache: {e}")
            # Fallback to no cache if necessary (though it will fail later if not handled)
            raise

    def _build_reference_text(self) -> str:
        """Combines varieties, farms, and processes into a single reference text."""
        sections = []

        # 1. Varieties
        varieties_data = self._read_json("varietal_mappings.json")
        v_lines = ["COFFEE VARIETIES:"]
        v_grouped = {}
        for entry in varieties_data:
            canonical = entry.get("canonical_names", [None])[0] or entry.get("original_name")
            if not canonical:
                continue
            aliases = set(entry.get("canonical_names", []) + [entry.get("original_name", "")])
            if canonical not in v_grouped:
                v_grouped[canonical] = set()
            v_grouped[canonical].update(aliases)

        for canonical, aliases in sorted(v_grouped.items()):
            alias_str = ", ".join(sorted([a for a in aliases if a and a != canonical]))
            v_lines.append(f"- ID: {canonical}" + (f" (Aliases: {alias_str})" if alias_str else ""))
        sections.append("\n".join(v_lines))

        # 2. Farms
        farms_data = self._read_json("farm_mappings.json")
        f_lines = ["COFFEE FARMS & ORGANIZATIONS:"]
        f_grouped = {}
        for entry in farms_data:
            canonical = entry.get("canonical_farm_name")
            if not canonical:
                continue
            location = f"{entry.get('region', '')}, {entry.get('country', '')}".strip(", ")
            if canonical not in f_grouped:
                f_grouped[canonical] = set()
            if location:
                f_grouped[canonical].add(location)

        for canonical, locations in sorted(f_grouped.items()):
            loc_str = " | ".join(sorted(locations))
            f_lines.append(f"- ID: {canonical}" + (f" [{loc_str}]" if loc_str else ""))
        sections.append("\n".join(f_lines))

        # 3. Processes
        processes_data = self._read_json("processing_methods_mappings.json")
        p_lines = ["PROCESSING METHODS:"]
        p_grouped = {}
        for entry in processes_data:
            canonical = entry.get("common_name") or entry.get("original_name")
            if not canonical:
                continue
            original = entry.get("original_name")
            if canonical not in p_grouped:
                p_grouped[canonical] = set()
            if original:
                p_grouped[canonical].add(original)

        # Add common industry synonyms that might be missing from the mappings
        if "Wet Hulled" in p_grouped:
            p_grouped["Wet Hulled"].add("Giling Basah")
            p_grouped["Wet Hulled"].add("Wet-Hulled")

        for canonical, aliases in sorted(p_grouped.items()):
            alias_str = ", ".join(sorted([a for a in aliases if a and a != canonical]))
            p_lines.append(f"- ID: {canonical}" + (f" (Aliases: {alias_str})" if alias_str else ""))
        sections.append("\n".join(p_lines))

        return "\n\n".join(sections)

    def _read_json(self, filename: str) -> list:
        path = Path(__file__).parent.parent / "database" / filename
        if not path.exists():
            return []
        try:
            with open(path) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading {filename}: {e}")
            return []

    def _get_segmenter_prompt(self) -> str:
        return """
You are a specialty coffee expert and technical analyst.
Your task is to analyze a podcast transcript and divide it into meaningful topical segments.

The transcript is provided as timestamped chunks. Use the actual chunk timestamps to determine
the start and end times for each segment. Do NOT estimate or approximate timestamps.

For each segment:
1. Identify the topic (e.g., 'Alternative fermentation methods', 'History of Geisha in Panama').
2. Provide a concise summary.
3. Extract the start timestamp from the first relevant chunk and the end timestamp from the last
   relevant chunk.
4. Provide a key takeaway representing the most interesting insight from this segment.

NOTE: Do NOT worry about extracting entities or relationships in this pass. Focus on clean
segment boundaries and summaries.
"""

    def _get_extractor_prompt(self) -> str:
        return """
You are a specialty coffee expert. Your task is to extract specific coffee entities from a segment of a podcast transcript.

Entity types to extract:
- variety: Specific coffee cultivars (e.g., Sidra, SL28, Gesha, Pink Bourbon, Bourbon, Typica).
- farm: Named farms, estates, cooperatives, wet mills, or producer organizations.
- producer: Coffee producers or farmers mentioned by name. Also tag coffee roasters or roasting companies here.
- process: Processing methods and fermentation techniques.
- origin: Named countries, regions, or specific geographic locations.

Do NOT extract:
- Importers, exporters, or marketing agents (e.g., Nordic Approach, Melbourne Coffee Merchants)
- Podcast hosts, interviewers, or industry commentators
- Generic business entities unrelated to growing or roasting coffee

Mapping Requirements:
1. For every extracted 'variety', 'farm', or 'process', search the COFFEE REFERENCE LIBRARY for a matching entry.
2. The 'canonical_id' MUST be copied EXACTLY as it appears after "ID:" in the reference library. Do NOT paraphrase, reformat, or invent canonical IDs.
3. If there is no entry in the reference library that clearly matches, set 'canonical_id' to null. It is better to return null than to guess or fabricate an ID.
4. If a name is misspelled in the transcript (e.g., 'Nascimento' instead of 'Nacimiento'), check the Aliases in the library to find the correct entry and use its exact "ID:" value.
5. If the transcript uses a common synonym (e.g., 'Giling Basah' for 'Wet Hulled'), map it to the correct canonical ID if present in the library aliases.
6. Only extract entities explicitly mentioned or clearly referred to in the text.

CRITICAL: You MUST strictly adhere to the IDs provided. If you extract 'giling basah' and 'Wet Hulled' is an ID in the library, you MUST use 'Wet Hulled' as the canonical_id.

Examples of CORRECT behavior:
- Library has "ID: Los Pirineos" → canonical_id must be "Los Pirineos" (NOT "Finca Los Pirineos")
- Library has "ID: Finca Nacimiento" → canonical_id must be "Finca Nacimiento" (NOT "Finca El Nacimiento")
- Transcript says "Giling Basah" and Library has "ID: Wet Hulled (Aliases: Giling Basah)" → canonical_id must be "Wet Hulled"
- Entity not found in library → canonical_id must be null (NOT an invented name)
"""

    async def analyze_episode(self, transcript_path: Path) -> PodcastEpisodeAnalysis:
        with open(transcript_path) as f:
            data = json.load(f)

        # Handle both formats:
        # 1. Single dict: {"text": "...", "chunks": [...]}
        # 2. Array of segments: [{"text": "...", "chunks": [...]}, ...]
        if isinstance(data, list):
            chunks = []
            for segment in data:
                chunks.extend(segment.get("chunks", []))
        else:
            chunks = data.get("chunks", [])

        # Build a timestamped transcript for the LLM
        timestamped_lines = []
        for chunk in chunks:
            text = chunk.get("text", "").strip()
            ts = chunk.get("timestamp", [0, 0])
            if text:
                start = ts[0] if len(ts) > 0 else 0
                timestamped_lines.append(f"[{start:.1f}s] {text}")

        timestamped_transcript = "\n".join(timestamped_lines)
        full_text = " ".join(c.get("text", "") for c in chunks)
        podcast_name = transcript_path.parent.name
        episode_slug = transcript_path.stem

        # Determine media type based on directory
        media_type = "podcast"
        if "blog_data" in str(transcript_path):
            media_type = "blog"
        elif "youtube" in str(transcript_path):
            media_type = "video"

        try:
            if media_type == "blog":
                # Simplified flow for blogs: treat as a single segment
                logger.info(f"Analyzing blog post: {episode_slug} (single segment mode)")
                segment_prompt = (
                    "Analyze this blog post. You MUST provide exactly ONE segment that summarizes the entire content.\n"
                    f"id: {episode_slug}\n"
                    f"podcast_name: {podcast_name}\n"
                    f"media_type: blog\n\n"
                    f"Text:\n{full_text}"
                )
                result = await self.segmenter.run(segment_prompt)
                analysis = result.output
                analysis.id = episode_slug
                analysis.podcast_name = podcast_name
                analysis.media_type = "blog"

                # Force exactly one segment for blogs to simplify tagging
                if not analysis.segments:
                    analysis.segments = [
                        PodcastSegment(
                            title=analysis.episode_title,
                            summary="Summary of the blog post.",
                            timestamp_start=0.0,
                            timestamp_end=0.0,
                        )
                    ]
                elif len(analysis.segments) > 1:
                    logger.info(f"Collapsing {len(analysis.segments)} segments into one for blog {episode_slug}")
                    first = analysis.segments[0]
                    first.title = analysis.episode_title
                    first.summary = " ".join(s.summary for s in analysis.segments)
                    first.key_takeaway = analysis.segments[-1].key_takeaway
                    analysis.segments = [first]

                analysis.segments[0].timestamp_start = 0.0
                analysis.segments[0].timestamp_end = 0.0
                analysis.segments[0].raw_text = full_text
            else:
                # Standard flow for podcasts/videos: segment into topics
                prompt = (
                    f"Analyze this {media_type} and segment it.\n"
                    f"id: {episode_slug}\n"
                    f"podcast_name: {podcast_name}\n"
                    f"media_type: {media_type}\n\n"
                    f"Timestamped Transcript:\n{timestamped_transcript}"
                )

                # Stage 1: Segmentation
                result = await self.segmenter.run(prompt)
                analysis = result.output
                analysis.id = episode_slug
                analysis.podcast_name = podcast_name
                analysis.media_type = media_type

                # Post-process: populate raw_text on each segment from chunks
                self._fill_raw_text(analysis, chunks)

            # Stage 2: Parallel Entity Extraction
            semaphore = asyncio.Semaphore(5)  # Throttle to avoid rate limits

            async def extract_segment(segment: PodcastSegment):
                # Ensure we have text to extract from
                text_to_extract = segment.raw_text or ""
                if not text_to_extract:
                    return

                async with semaphore:
                    logger.debug(f"Extracting entities from segment: {segment.title}")
                    ext_result = await self.extractor.run(f"Extract entities from this segment:\n\n{text_to_extract}")
                    segment.entities = ext_result.output.entities
                    if segment.entities:
                        logger.debug(f"Extracted {len(segment.entities)} entities for '{segment.title}'")
                        for ent in segment.entities:
                            logger.debug(f"  - {ent.entity_type}: {ent.raw_name} -> {ent.canonical_id}")

            await asyncio.gather(*(extract_segment(s) for s in analysis.segments))

            return analysis
        except Exception as e:
            logger.error(f"Error analyzing episode {transcript_path}: {e}")
            raise

    def _fill_raw_text(self, analysis: PodcastEpisodeAnalysis, chunks: list):
        """Slice transcript chunks by segment timestamps to populate raw_text.
        Chunks overlapping multiple segments are assigned based on the majority overlap
        to keep segments clean.
        """
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

                # Assign chunk to segment if its midpoint is within the segment range
                # This prevents duplication across boundaries
                chunk_mid = (chunk_start + chunk_end) / 2
                if segment.timestamp_start <= chunk_mid < segment.timestamp_end:
                    texts.append(text)
            segment.raw_text = " ".join(texts)

async def main():
    import sys
    logging.basicConfig(level=logging.INFO)
    tagger = PodcastTagger()

    # Example usage: uv run python3 -m src.kissaten.ai.podcast_tagger podcast_data/path/to/file.json
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
