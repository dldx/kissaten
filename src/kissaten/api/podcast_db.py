"""Separate DuckDB database for podcast/media data.

This module manages a dedicated podcasts.duckdb file, independent from the
main kissaten.duckdb used for coffee bean data.
"""

import os
import re
import unicodedata
from pathlib import Path

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

    try:
        # Clear existing data for a full refresh
        podcast_conn.execute("DELETE FROM podcast_segment_entities")
        podcast_conn.execute("DELETE FROM podcast_segments")
        podcast_conn.execute("DELETE FROM podcast_episodes")
        podcast_conn.commit()

        # 1. Load Episodes
        podcast_conn.execute(f"""
            INSERT OR IGNORE INTO podcast_episodes
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
                segment_id || '_' || (row_number() over ())::VARCHAR as id,
                segment_id,
                entity['entity_type'] as entity_type,
                CASE
                    WHEN entity['entity_type'] = 'variety' THEN normalize_varietal_name(entity['raw_name'])
                    WHEN entity['entity_type'] = 'process' THEN normalize_process_name(entity['raw_name'])
                    ELSE entity['raw_name']
                END as canonical_id,
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


async def search_podcasts(
    query: str,
    limit: int = 5,
    process_filter: str | None = None,
    variety_filter: str | None = None,
    origin_filter: str | None = None,
) -> list[PodcastSearchHit]:
    """
    Search for podcast segments using weighted FTS and entity matches.
    """
    sql = """
        WITH fts_results AS (
            SELECT
                segment_id,
                fts_main_podcast_segments_fts_source.match_bm25(
                    segment_id,
                    ?
                ) as bm25_score
            FROM podcast_segments_fts_source
        ),
        entity_matches AS (
            SELECT
                segment_id,
                list(raw_mention) as matched_entities,
                count(*) filter (where lower(canonical_id) = lower(?)) as process_match,
                count(*) filter (where lower(canonical_id) = lower(?)) as variety_match,
                count(*) filter (where lower(canonical_id) = lower(?)) as origin_match
            FROM podcast_segment_entities
            GROUP BY segment_id
        )
        SELECT
            s.segment_id,
            s.episode_id,
            e.podcast_name,
            e.episode_title,
            e.url,
            s.title,
            s.summary,
            s.timestamp_start,
            s.timestamp_end,
            s.key_takeaway,
            s.raw_text,
            COALESCE(fts.bm25_score, 0) +
            (CASE WHEN s.title ILIKE ? THEN 10.0 ELSE 0 END) +
            (CASE WHEN s.summary ILIKE ? THEN 5.0 ELSE 0 END) +
            (CASE WHEN em.process_match > 0 THEN 20.0 ELSE 0 END) +
            (CASE WHEN em.variety_match > 0 THEN 20.0 ELSE 0 END) +
            (CASE WHEN em.origin_match > 0 THEN 20.0 ELSE 0 END) as relevance_score,
            COALESCE(em.matched_entities, []) as matched_entities
        FROM podcast_segments s
        JOIN podcast_episodes e ON s.episode_id = e.episode_id
        LEFT JOIN fts_results fts ON s.segment_id = fts.segment_id
        LEFT JOIN entity_matches em ON s.segment_id = em.segment_id
        WHERE (fts.bm25_score IS NOT NULL OR s.title ILIKE ? OR s.summary ILIKE ?)
           OR (em.process_match > 0 OR em.variety_match > 0 OR em.origin_match > 0)
        ORDER BY relevance_score DESC
        LIMIT ?
    """

    search_term = f"%{query}%"
    try:
        results = podcast_conn.execute(
            sql,
            [
                query,  # FTS query
                process_filter,
                variety_filter,
                origin_filter,
                search_term,  # Title ILIKE
                search_term,  # Summary ILIKE
                search_term,  # WHERE Title ILIKE
                search_term,  # WHERE Summary ILIKE
                limit,
            ],
        ).fetchall()
    except Exception as e:
        print(f"Search error: {e}")
        return []

    hits = []
    for row in results:
        hits.append(
            PodcastSearchHit(
                segment_id=row[0],
                episode_id=row[1],
                podcast_name=row[2],
                episode_title=row[3],
                url=row[4],
                title=row[5],
                summary=row[6],
                timestamp_start=row[7],
                timestamp_end=row[8],
                key_takeaway=row[9],
                raw_text=row[10],
                relevance_score=row[11],
                matched_entities=row[12],
            )
        )

    return hits


async def main():
    """Initialize podcast database and load all podcast data."""
    await init_podcast_database()
    podcast_dir = Path(__file__).parent.parent.parent.parent / "podcast_data"
    await load_podcast_data(podcast_dir)
    podcast_conn.close()
