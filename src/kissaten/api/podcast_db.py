"""Separate DuckDB database for podcast/media data.

This module manages a dedicated podcasts.duckdb file, independent from the
main kissaten.duckdb used for coffee bean data.
"""

import asyncio
import json
import logging
import os
import re
import unicodedata
from pathlib import Path
from typing import Any, List, Optional

import duckdb
import httpx
from aiocache import cached
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from rich.console import Console

from kissaten.cache.media_insights_cache import MediaInsightsCache
from kissaten.schemas.podcast import PodcastSearchHit

console = Console(force_terminal=True)
media_cache = MediaInsightsCache()
logger = logging.getLogger(__name__)


def _get_podcast_database_path() -> Path:
    """Get the podcast database path."""
    env_path = os.environ.get("KISSATEN_PODCAST_DATABASE_PATH")
    if env_path:
        return Path(env_path)
    return Path(__file__).parent.parent.parent.parent / "data" / "podcasts.duckdb"


_db_config = {"enable_external_access": True}
podcast_conn = duckdb.connect(str(_get_podcast_database_path()), config=_db_config)


def normalize_process_name(process: str) -> str:
    """Normalize process name for URL-friendly slugs."""
    if not process:
        return ""
    nfkd_form = unicodedata.normalize("NFKD", process)
    ascii_only = nfkd_form.encode("ASCII", "ignore").decode("ASCII")
    normalized = re.sub(r"[^a-zA-Z0-9\s-]", "", ascii_only.lower())
    normalized = re.sub(r"[\s-]+", "-", normalized.strip())
    return normalized


def normalize_varietal_name(varietal: str) -> str:
    """Normalize varietal name for URL-friendly slugs."""
    if not varietal:
        return ""
    nfkd_form = unicodedata.normalize("NFKD", varietal)
    ascii_only = nfkd_form.encode("ASCII", "ignore").decode("ASCII")
    normalized = re.sub(r"[^a-zA-Z0-9\s-]", "", ascii_only.lower())
    normalized = re.sub(r"[\s-]+", "-", normalized.strip())
    return normalized


def _register_podcast_udfs() -> None:
    """Register UDFs needed for podcast entity normalization."""
    _udfs = [
        ("normalize_process_name", normalize_process_name, [str], str, {}),
        ("normalize_varietal_name", normalize_varietal_name, [str], str, {}),
    ]
    for name, func, params, ret, kwargs in _udfs:
        try:
            podcast_conn.remove_function(name)
        except Exception:
            pass
        try:
            podcast_conn.create_function(name, func, params, ret, **kwargs)
        except Exception as e:
            if "already exists" not in str(e).lower():
                raise


_register_podcast_udfs()


async def init_podcast_database():
    """Create podcast tables if they don't exist."""
    podcast_conn.execute("INSTALL fts")
    podcast_conn.execute("LOAD fts")

    podcast_conn.execute("""
        CREATE TABLE IF NOT EXISTS podcast_episodes (
            episode_id VARCHAR PRIMARY KEY,
            podcast_name VARCHAR,
            episode_title VARCHAR,
            media_type VARCHAR,
            url VARCHAR,
            audio_url VARCHAR,
            published_date VARCHAR,
            source_path VARCHAR
        )
    """)
    podcast_conn.execute("""
        CREATE TABLE IF NOT EXISTS podcast_segments (
            segment_id VARCHAR PRIMARY KEY,
            episode_id VARCHAR,
            title VARCHAR,
            summary VARCHAR,
            timestamp_start DOUBLE,
            timestamp_end DOUBLE,
            key_takeaway VARCHAR,
            raw_text VARCHAR,
            FOREIGN KEY (episode_id) REFERENCES podcast_episodes(episode_id)
        )
    """)
    podcast_conn.execute("""
        CREATE TABLE IF NOT EXISTS podcast_segment_entities (
            id VARCHAR,
            segment_id VARCHAR,
            entity_type VARCHAR,
            canonical_id VARCHAR,
            raw_mention VARCHAR,
            FOREIGN KEY (segment_id) REFERENCES podcast_segments(segment_id)
        )
    """)
    podcast_conn.commit()


def rebuild_podcast_fts_index():
    """Rebuild the podcast segments FTS index from current data."""
    try:
        podcast_conn.execute("DROP VIEW IF EXISTS podcast_segments_fts_source")
    except Exception:
        pass
    try:
        podcast_conn.execute("DROP TABLE IF EXISTS podcast_segments_fts_source")
    except Exception:
        pass
    podcast_conn.execute("""
        CREATE TABLE podcast_segments_fts_source AS
        SELECT
            segment_id,
            episode_id,
            title,
            summary,
            key_takeaway,
            raw_text
        FROM podcast_segments
    """)
    row_count = podcast_conn.execute("SELECT count(*) FROM podcast_segments_fts_source").fetchone()[0]
    if row_count > 0:
        podcast_conn.execute(
            "PRAGMA create_fts_index('podcast_segments_fts_source', 'segment_id', 'title', 'summary', 'key_takeaway', 'raw_text', overwrite=1)"
        )
        print(f"Podcast FTS index created with {row_count} segments")
    elif row_count == 0:
        print("No podcast segments to index")


async def load_podcast_data(podcast_dir: Path):
    """Load podcast/blog/media analysis JSON files into the podcast DuckDB.

    Args:
        podcast_dir: Path to root project directory or a specific *_data folder.
    """
    # Resolve data_dir: if called with a *_data folder, go up one level
    if podcast_dir.name in ("podcast_data", "blog_data", "youtube_data"):
        data_dir = podcast_dir.parent
    else:
        data_dir = podcast_dir

    # Define search patterns for all media types
    media_dirs = {
        "podcast": data_dir / "podcast_data",
        "blog": data_dir / "blog_data",
        "video": data_dir / "youtube_data",
    }

    try:
        # Clear existing data for a full refresh
        podcast_conn.execute("DELETE FROM podcast_segment_entities")
        podcast_conn.execute("DELETE FROM podcast_segments")
        podcast_conn.execute("DELETE FROM podcast_episodes")
        podcast_conn.commit()

        # 1. Load Episodes from Analysis
        for media_type, media_dir in media_dirs.items():
            # Check if directory exists before reading
            if not media_dir.exists():
                continue

            analysis_files = list(media_dir.glob("**/*.analysis.json"))
            if not analysis_files:
                continue

            pattern = str(media_dir / "**" / "*.analysis.json")

            podcast_conn.execute(f"""
                INSERT INTO podcast_episodes (episode_id, podcast_name, episode_title, media_type, url, source_path)
                SELECT
                    coalesce(id, regexp_extract(filename, '([^/]+)\\.analysis\\.json', 1)) as ep_id,
                    coalesce(podcast_name, regexp_extract(filename, '(_data)/([^/]+)/', 2)) as pd_name,
                    episode_title,
                    '{media_type}' as m_type,
                    url,
                    filename as src_path
                FROM read_json('{pattern}',
                    filename=true,
                    auto_detect=true,
                    union_by_name=true
                )
            """)

            # Merge Metadata for this type
            metadata_files = list(media_dir.glob("**/*.metadata.json"))
            if metadata_files:
                meta_pattern = str(media_dir / "**" / "*.metadata.json")
                # Check if audio_url exists in metadata (podcasts have it, blogs don't)
                has_audio = media_type == "podcast"
                if has_audio:
                    podcast_conn.execute(f"""
                        INSERT INTO podcast_episodes (episode_id, url, audio_url, published_date)
                        SELECT
                            regexp_extract(filename, '([^/]+)\\.metadata\\.json', 1) as ep_id,
                            url,
                            audio_url,
                            published_date
                        FROM read_json('{meta_pattern}',
                            filename=true,
                            auto_detect=true,
                            union_by_name=true
                        )
                        ON CONFLICT(episode_id) DO UPDATE SET
                            url = COALESCE(excluded.url, podcast_episodes.url),
                            audio_url = excluded.audio_url,
                            published_date = excluded.published_date
                    """)
                else:
                    podcast_conn.execute(f"""
                        INSERT INTO podcast_episodes (episode_id, url, published_date)
                        SELECT
                            regexp_extract(filename, '([^/]+)\\.metadata\\.json', 1) as ep_id,
                            url,
                            published_date
                        FROM read_json('{meta_pattern}',
                            filename=true,
                            auto_detect=true,
                            union_by_name=true
                        )
                        ON CONFLICT(episode_id) DO UPDATE SET
                            url = COALESCE(excluded.url, podcast_episodes.url),
                            published_date = excluded.published_date
                    """)

            # 2. Load Segments for this type
            podcast_conn.execute(f"""
                INSERT OR IGNORE INTO podcast_segments
                SELECT
                    coalesce(id, regexp_extract(filename, '([^/]+)\\.analysis\\.json', 1)) || '_' || segment_idx as segment_id,
                    coalesce(id, regexp_extract(filename, '([^/]+)\\.analysis\\.json', 1)) as episode_id,
                    segment.title,
                    segment.summary,
                    segment.timestamp_start,
                    segment.timestamp_end,
                    segment.key_takeaway,
                    segment.raw_text
                FROM (
                    SELECT
                        id,
                        filename,
                        unnest(segments) as segment,
                        generate_subscripts(segments, 1) - 1 as segment_idx
                    FROM read_json('{pattern}',
                        filename=true,
                        auto_detect=true,
                        union_by_name=true
                    )
                )
            """)

            # 3. Load Entities for this type
            podcast_conn.execute(f"""
                INSERT INTO podcast_segment_entities
                SELECT
                    segment_id || '_ent_' || (row_number() over ())::VARCHAR as id,
                    segment_id,
                    entity['entity_type'] as entity_type,
                    entity['canonical_id'] as canonical_id,
                    entity['raw_name'] as raw_mention
                FROM (
                    SELECT
                        coalesce(id, regexp_extract(filename, '([^/]+)\\.analysis\\.json', 1)) || '_' || segment_idx as segment_id,
                        unnest(segment.entities) as entity
                    FROM (
                        SELECT
                            id,
                            filename,
                            unnest(segments) as segment,
                            generate_subscripts(segments, 1) - 1 as segment_idx
                        FROM read_json('{pattern}',
                            filename=true,
                            auto_detect=true,
                            union_by_name=true
                        )
                    )
                    WHERE len(segment.entities) > 0
                )
            """)

        podcast_conn.commit()

        result = podcast_conn.execute("SELECT COUNT(*) FROM podcast_episodes").fetchone()
        ep_count = result[0] if result else 0
        result = podcast_conn.execute("SELECT COUNT(*) FROM podcast_segments").fetchone()
        seg_count = result[0] if result else 0
        print(f"Loaded {ep_count} episodes/posts and {seg_count} segments into media database")

        # Rebuild FTS index now that segments are populated
        rebuild_podcast_fts_index()

    except Exception as e:
        print(f"Error loading podcast data: {e}")
        raise


class SegmentRelevance(BaseModel):
    segment_id: str
    is_relevant: bool = Field(..., description="Whether the segment is truly relevant to the query")
    relevance_score: float = Field(..., description="0-100 score of how well it matches")
    explanation: str = Field(..., description="Brief reason for the decision")


class RerankResponse(BaseModel):
    results: list[SegmentRelevance]


reranker_agent = Agent(
    "google-gla:gemini-3.1-flash-lite",
    output_type=RerankResponse,
    system_prompt="""
You are a coffee search expert. Your task is to review a set of podcast/blog segments and determine if they are truly relevant to a user's coffee-related query.

Relevance Guidelines:
- High relevance: The segment directly discusses the specific farm, producer, varietal, or process in the query.
- High relevance: Educational content explaining the topic (e.g. explaining what "anaerobic" means if the query is about anaerobic process).
- Inclusion: Even if mentioned briefly, if it's a specific proper noun like a farm name (e.g. "Kerehaklu Estate") or a rare varietal, it IS relevant.

Strictly filter out:
1. Purely transitional segments (intro/outro music, host banter).
2. Segments that mention the keyword but are NOT about that specific coffee topic (e.g., mentioning "Geisha" as a metaphor for expensive).
3. Redundant segments that add no new information.
4. Segments where the topic is only briefly mentioned as part of a long unrelated list.

For each segment, provide:
- is_relevant: true/false
- relevance_score: 0 to 100
- explanation: why it is or isn't relevant to the specific coffee query.
""",
)


@cached(ttl=3600)
async def get_jina_rerank(query: str, documents: tuple[str, ...], top_n: int) -> Optional[dict]:
    """Call Jina AI reranker with caching."""
    api_key = os.environ.get("JINA_API_KEY")
    if not api_key:
        return None

    print(f"JINA API CALL: reranking {len(documents)} docs for query: {query[:50]}...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.jina.ai/v1/rerank",
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
                json={
                    "model": "jina-reranker-v3",
                    "query": query,
                    "top_n": top_n,
                    "documents": list(documents),
                    "return_documents": False,
                },
                timeout=12.0,
            )

            if response.status_code == 200:
                return response.json()
            else:
                print(f"Jina API error {response.status_code}: {response.text}")
                return None
    except Exception as e:
        print(f"Jina API exception: {e}")
        return None


async def search_podcasts(
    query: str,
    limit: int = 5,
    process_filter: list[str] | None = None,
    variety_filter: list[str] | None = None,
    origin_filter: str | None = None,
    producer_filter: str | None = None,
    rerank: bool = True,
    ai_rerank: bool = True,
) -> list[PodcastSearchHit]:
    """
    Search for podcast segments using weighted FTS and entity matches.
    """
    # 0. Normalize inputs for stable hashing and querying
    query = query.strip() if query else ""
    # Deduplicate and sort lists to ensure stability regardless of param order
    process_filter = sorted(list(set([p.strip() for p in (process_filter or []) if p.strip()])))
    variety_filter = sorted(list(set([v.strip() for v in (variety_filter or []) if v.strip()])))
    origin_filter = origin_filter.strip() if origin_filter else None
    producer_filter = producer_filter.strip() if producer_filter else None

    # 0.1 Check Cache
    search_params = {
        "query": query,
        "limit": limit,
        "process_filter": process_filter,
        "variety_filter": variety_filter,
        "origin_filter": origin_filter,
        "producer_filter": producer_filter,
        "rerank": rerank,
        "ai_rerank": ai_rerank,
    }
    query_hash = media_cache.generate_query_hash(search_params)
    cached_hit = media_cache.get_cached_results(query_hash)
    if cached_hit:
        logger.info(f"CACHE HIT (Query): {query_hash[:8]}... Returning {len(cached_hit.hits)} results.")
        return cached_hit.hits

    # 0.2 Construct a meaningful query for the reranker if the user query is empty
    # or just a repeat of the filters.
    rerank_query = query
    if not rerank_query:
        parts = []
        if process_filter:
            parts.append(f"coffee processing methods: {', '.join(process_filter)}")
        if variety_filter:
            parts.append(f"coffee varieties: {', '.join(variety_filter)}")
        if origin_filter:
            parts.append(f"coffee origin: {origin_filter}")
        if producer_filter:
            parts.append(f"coffee producer or farm: {producer_filter}")
        rerank_query = " and ".join(parts)

    # If reranking, we expand the initial search to get more candidates
    # We cap at 3x or 30 total to avoid hitting Jina token limits
    initial_limit = min(limit * 3, 30) if rerank and rerank_query else limit

    # Use normalized filters for SQL (conversion to lowercase)
    varieties = [v.lower() for v in variety_filter]
    processes = [p.lower() for p in process_filter]

    # Quick check for zero hits in Stage 1
    # We use a lightweight count query to avoid overhead if we can
    # But for simplicity, we'll just run the main query.

    sql = """
        WITH fts_results AS (
            SELECT
                segment_id,
                fts_main_podcast_segments_fts_source.match_bm25(
                    segment_id,
                    ?
                ) as bm25_score
            FROM podcast_segments_fts_source
            WHERE ? != ''
        ),
        entity_matches AS (
            SELECT
                segment_id,
                list(raw_mention) as matched_entities,
                count(*) filter (where (len(?) > 0 AND (lower(canonical_id) = ANY(?) OR lower(raw_mention) = ANY(?)))) as process_match,
                count(*) filter (where (len(?) > 0 AND (lower(canonical_id) = ANY(?) OR lower(raw_mention) = ANY(?)))) as variety_match,
                count(*) filter (where (lower(canonical_id) = lower(?) OR lower(raw_mention) = lower(?))) as origin_match,
                count(*) filter (where (lower(canonical_id) ILIKE ? OR lower(raw_mention) ILIKE ? OR ? ILIKE '%' || lower(canonical_id) || '%' OR ? ILIKE '%' || lower(raw_mention) || '%')) as producer_match
            FROM podcast_segment_entities
            GROUP BY segment_id
        )
        SELECT
            s.segment_id,
            s.episode_id,
            e.podcast_name,
            e.episode_title,
            e.url,
            e.audio_url,
            e.published_date,
            e.media_type,
            s.title,
            s.summary,
            s.timestamp_start,
            s.timestamp_end,
            COALESCE(fts.bm25_score, 0) +
            (CASE WHEN ? != '' AND s.title ILIKE ? THEN 10.0 ELSE 0 END) +
            (CASE WHEN ? != '' AND s.summary ILIKE ? THEN 5.0 ELSE 0 END) +
            (CASE WHEN em.process_match > 0 THEN 20.0 ELSE 0 END) +
            (CASE WHEN em.variety_match > 0 THEN 20.0 ELSE 0 END) +
            (CASE WHEN em.origin_match > 0 THEN 20.0 ELSE 0 END) +
            (CASE WHEN em.producer_match > 0 THEN 20.0 ELSE 0 END) as relevance_score,
            COALESCE(em.matched_entities, []) as matched_entities,
            s.raw_text
        FROM podcast_segments s
        JOIN podcast_episodes e ON s.episode_id = e.episode_id
        LEFT JOIN fts_results fts ON s.segment_id = fts.segment_id
        LEFT JOIN entity_matches em ON s.segment_id = em.segment_id
        WHERE (
            (? != '' AND (fts.bm25_score IS NOT NULL OR s.title ILIKE ? OR s.summary ILIKE ?))
            OR (em.process_match > 0 OR em.variety_match > 0 OR em.origin_match > 0 OR em.producer_match > 0)
        )
        -- If a producer/farm filter is provided, ONLY return hits that match that specific producer (via entity OR text)
        AND (CASE WHEN ? IS NOT NULL THEN (em.producer_match > 0 OR s.title ILIKE ? OR s.summary ILIKE ?) ELSE TRUE END)
        ORDER BY relevance_score DESC
        LIMIT ?
    """

    search_term = f"%{query}%"
    producer_term = f"%{producer_filter}%" if producer_filter else None

    try:
        results = podcast_conn.execute(
            sql,
            [
                query,  # FTS query
                query,  # FTS condition check
                processes,
                processes,
                processes,
                varieties,
                varieties,
                varieties,
                origin_filter,
                origin_filter,
                producer_term,  # producer_match - ILIKE
                producer_term,  # producer_match - ILIKE
                producer_filter,  # producer_match - contains filter
                producer_filter,  # producer_match - contains filter
                query,
                search_term,  # Title bonus
                query,
                search_term,  # Summary bonus
                query,
                search_term,
                search_term,  # Main query filter
                producer_filter,  # Mandatory producer filter check
                producer_term,  # Mandatory producer filter - title ILIKE
                producer_term,  # Mandatory producer filter - summary ILIKE
                initial_limit,
            ],
        ).fetchall()
    except Exception as e:
        print(f"Search error: {e}")
        return []

    hits = []
    documents = []
    raw_texts = {}
    for row in results:
        hit = PodcastSearchHit(
            segment_id=row[0],
            episode_id=row[1],
            podcast_name=row[2],
            episode_title=row[3],
            url=row[4],
            audio_url=row[5],
            published_date=row[6],
            media_type=row[7],
            title=row[8],
            summary=row[9],
            timestamp_start=row[10],
            timestamp_end=row[11],
            relevance_score=row[12],
            matched_entities=row[13],
        )
        hits.append(hit)
        raw_texts[row[0]] = row[14]
        # Truncate raw_text to ~400 words (2000 chars) to stay within Jina rate limits
        # while providing enough context for accurate reranking.
        truncated_text = (row[14][:2000] + "...") if row[14] and len(row[14]) > 2000 else (row[14] or "")
        documents.append(f"{row[7]}\n{truncated_text}")

    # Check if we have any results at all
    if not hits:
        # Cache the empty result for this query_hash so we don't look again
        # results_hash for empty results can be a stable static string
        media_cache.cache_results(query_hash, "EMPTY_STAGE_1", [])
        return []

    # Check if we can use cached results
    results_hash = media_cache.generate_results_hash(hits)
    if cached_hit and cached_hit.results_hash == results_hash:
        print(f"MEDIA CACHE HIT: Serving {len(cached_hit.hits)} results instantly")
        return cached_hit.hits

    # Optimization: Even if query_hash was a miss, if these Stage 1 hits
    # have been reranked before, reuse those results.
    data_match_hits = media_cache.get_cached_results_by_data(results_hash)
    if data_match_hits:
        print(f"MEDIA CACHE HIT (Data Match): Reusing reranked results for hash {results_hash[:8]}")
        # Backfill this specific query_hash so next time it's a direct hit
        media_cache.cache_results(query_hash, results_hash, data_match_hits)
        return data_match_hits

    # Stage 2: Reranking with Jina AI
    if rerank and rerank_query and hits:
        # Convert documents to tuple for caching (must be hashable)
        rerank_data = await get_jina_rerank(rerank_query, tuple(documents), limit)

        if rerank_data:
            new_hits = []
            for outcome in rerank_data.get("results", []):
                idx = outcome["index"]
                original_hit = hits[idx]
                # Update relevance score with Jina's confidence
                original_hit.relevance_score = outcome["relevance_score"] * 100
                new_hits.append(original_hit)
            hits = new_hits
        else:
            # Fallback to initial top-N if rerank fails or returns None
            hits = hits[:limit]
    else:
        # If no reranking, just truncate to requested limit
        hits = hits[:limit]

    # Stage 3: Final AI Rerank and Discard (Gemini 3.1 Flash Lite)
    if ai_rerank and hits:
        print(f"AI RERANK: Reviewing {len(hits)} hits for '{query or rerank_query}'...")
        # Check if we already have a Stage 3 result for these specific Stage 1 hits
        # (Already handled by data_match_hits above, but being explicit here)
        segments_to_review = []
        for hit in hits:
            content = raw_texts.get(hit.segment_id) or ""
            segments_to_review.append(
                {
                    "segment_id": hit.segment_id,
                    "title": hit.title,
                    "summary": hit.summary,
                    "media_type": hit.media_type,
                    "content_snippet": content[:2000],
                }
            )

        try:
            ai_query_context = query or rerank_query
            prompt = f"User Query: {ai_query_context}\n\nSegments:\n{json.dumps(segments_to_review, indent=2)}"

            print(f"DEBUG: Running reranker_agent with {len(segments_to_review)} segments")
            result = await reranker_agent.run(prompt)

            print(f"DEBUG: reranker_agent result type: {type(result)}")
            if result is None:
                print("DEBUG: reranker_agent returned None")
                return hits

            # Access the structured data
            # In Pydantic AI, this is usually .data
            res_data = getattr(result, "data", None)
            if res_data is None:
                # Some versions/configs might use .output
                res_data = getattr(result, "output", None)

            # If the parser failed or returned None, fallback
            if res_data is None:
                # DO NOT cache as empty yet, as this might be a parsing error
                print(f"DEBUG: AI RERANK returned no data. Attributes available: {dir(result)}")
                return hits

            relevance_map = {r.segment_id: r for r in res_data.results}

            final_hits = []
            for hit in hits:
                rel = relevance_map.get(hit.segment_id)
                if rel and rel.is_relevant:
                    hit.relevance_score = rel.relevance_score
                    final_hits.append(hit)
                else:
                    reason = rel.explanation if rel else "No decision from AI"
                    print(f"AI RERANK: Discarding {hit.segment_id} ({hit.title}) - Reason: {reason}")

            # Sort by new scores
            final_hits.sort(key=lambda x: x.relevance_score, reverse=True)
            hits = final_hits[:limit]

            # Cache the successful AI result
            media_cache.cache_results(query_hash, results_hash, hits)
            return hits

        except Exception as e:
            print(f"AI Rerank error: {e}")
            # Fallback to hits from previous stages

    # 4. Save to Cache
    media_cache.cache_results(query_hash, results_hash, hits)

    return hits


async def main():
    """Initialize podcast database and load all podcast data."""
    await init_podcast_database()
    podcast_dir = Path(__file__).parent.parent.parent.parent / "podcast_data"
    await load_podcast_data(podcast_dir)
    podcast_conn.close()
