"""Separate DuckDB database for podcast/media data.

This module manages a dedicated podcasts.duckdb file, independent from the
main kissaten.duckdb used for coffee bean data.
"""

import os
import re
import unicodedata
import asyncio
import httpx
from pathlib import Path
from typing import Optional, List, Any
from aiocache import cached

import duckdb
from rich.console import Console

from kissaten.schemas.podcast import PodcastSearchHit

console = Console(force_terminal=True)


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
    else:
        print("No podcast segments to index")


async def load_podcast_data(podcast_dir: Path):
    """Load podcast analysis JSON files into the podcast DuckDB.

    Args:
        podcast_dir: Path to podcast_data directory containing .analysis.json files
    """
    if not podcast_dir.exists():
        print(f"Podcast directory not found: {podcast_dir}")
        return

    analysis_pattern = str(podcast_dir / "**" / "*.analysis.json")
    metadata_pattern = str(podcast_dir / "**" / "*.metadata.json")

    try:
        # Clear existing data for a full refresh
        podcast_conn.execute("DELETE FROM podcast_segment_entities")
        podcast_conn.execute("DELETE FROM podcast_segments")
        podcast_conn.execute("DELETE FROM podcast_episodes")
        podcast_conn.commit()

        # 1. Load Episodes from Analysis
        podcast_conn.execute(f"""
            INSERT INTO podcast_episodes (episode_id, podcast_name, episode_title, url, source_path)
            SELECT
                coalesce(id, regexp_extract(filename, '([^/]+)\\.analysis\\.json', 1)) as episode_id,
                coalesce(podcast_name, regexp_extract(filename, 'podcast_data/([^/]+)/', 1)) as podcast_name,
                episode_title,
                url,
                filename as source_path
            FROM read_json('{analysis_pattern}',
                filename=true,
                auto_detect=true,
                union_by_name=true
            )
        """)

        # 1b. Merge Metadata
        if list(podcast_dir.glob("**/*.metadata.json")):
            podcast_conn.execute(f"""
                INSERT INTO podcast_episodes (episode_id, url, audio_url, published_date)
                SELECT
                    regexp_extract(filename, '([^/]+)\\.metadata\\.json', 1) as episode_id,
                    url,
                    audio_url,
                    published_date
                FROM read_json('{metadata_pattern}',
                    filename=true,
                    auto_detect=true,
                    union_by_name=true
                )
                ON CONFLICT(episode_id) DO UPDATE SET
                    url = COALESCE(excluded.url, podcast_episodes.url),
                    audio_url = excluded.audio_url,
                    published_date = excluded.published_date
            """)

        # 2. Load Segments
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
                FROM read_json('{analysis_pattern}',
                    filename=true,
                    auto_detect=true,
                    union_by_name=true
                )
            )
        """)

        # 3. Load Entities
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
                    FROM read_json('{analysis_pattern}',
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
        print(f"Loaded {ep_count} podcast episodes and {seg_count} segments into podcast database")

        # Rebuild FTS index now that segments are populated
        rebuild_podcast_fts_index()

    except Exception as e:
        print(f"Error loading podcast data: {e}")
        raise


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
    process_filter: str | None = None,
    variety_filter: str | None = None,
    origin_filter: str | None = None,
    producer_filter: str | None = None,
    rerank: bool = True,
) -> list[PodcastSearchHit]:
    """
    Search for podcast segments using weighted FTS and entity matches.
    """
    # Construct a meaningful query for the reranker if the user query is empty
    rerank_query = query
    if not rerank_query:
        parts = []
        if process_filter:
            parts.append(f"coffee processing method: {process_filter}")
        if variety_filter:
            parts.append(f"coffee variety: {variety_filter}")
        if origin_filter:
            parts.append(f"coffee origin: {origin_filter}")
        if producer_filter:
            parts.append(f"coffee producer or farm: {producer_filter}")
        rerank_query = " and ".join(parts)

    # If reranking, we expand the initial search to get more candidates
    # We cap at 3x or 30 total to avoid hitting Jina token limits
    initial_limit = min(limit * 3, 30) if rerank and rerank_query else limit

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
                count(*) filter (where (lower(canonical_id) = lower(?) OR lower(raw_mention) = lower(?))) as process_match,
                count(*) filter (where (lower(canonical_id) = lower(?) OR lower(raw_mention) = lower(?))) as variety_match,
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
                process_filter,
                process_filter,
                variety_filter,
                variety_filter,
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
    for row in results:
        hit = PodcastSearchHit(
            segment_id=row[0],
            episode_id=row[1],
            podcast_name=row[2],
            episode_title=row[3],
            url=row[4],
            audio_url=row[5],
            published_date=row[6],
            title=row[7],
            summary=row[8],
            timestamp_start=row[9],
            timestamp_end=row[10],
            relevance_score=row[11],
            matched_entities=row[12],
        )
        hits.append(hit)
        # Truncate raw_text to ~400 words (2000 chars) to stay within Jina rate limits
        # while providing enough context for accurate reranking.
        truncated_text = (row[13][:2000] + "...") if row[13] and len(row[13]) > 2000 else row[13]
        documents.append(f"{row[7]}\n{truncated_text}")

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

    return hits


async def main():
    """Initialize podcast database and load all podcast data."""
    await init_podcast_database()
    podcast_dir = Path(__file__).parent.parent.parent.parent / "podcast_data"
    await load_podcast_data(podcast_dir)
    podcast_conn.close()
