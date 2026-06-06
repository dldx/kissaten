"""DuckDB-based cache for media search insights and AI reranking results."""

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional

import duckdb
from pydantic import TypeAdapter

from ..schemas.podcast import PodcastSearchHit

logger = logging.getLogger(__name__)

# Use TypeAdapter for serializing/deserializing lists of PodcastSearchHit
hits_adapter = TypeAdapter(List[PodcastSearchHit])


@dataclass
class MediaCacheHit:
    """Result of a media cache lookup."""

    hits: List[PodcastSearchHit]
    query_hash: str
    results_hash: str
    created_at: datetime

    @property
    def is_expired(self) -> bool:
        """Check if cache entry has expired (TTL of 7 days)."""
        if not self.created_at:
            return True
        # If created_at is naive, assume UTC
        dt = self.created_at
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - dt
        return delta.days > 7


class MediaInsightsCache:
    """Cache for media search results using DuckDB."""

    def __init__(self, cache_db_path: str | Path | None = None):
        """Initialize the media insights cache.

        Args:
            cache_db_path: Path to the DuckDB cache database file
        """
        import os

        if cache_db_path is None:
            env_path = os.environ.get("KISSATEN_MEDIA_CACHE_PATH")
            if env_path:
                cache_db_path = Path(env_path)
            elif os.environ.get("KISSATEN_USE_RW_DB") == "1":
                cache_db_path = Path(__file__).parent.parent.parent.parent / "data" / "rw_media_insights_cache.duckdb"
            else:
                cache_db_path = Path(__file__).parent.parent.parent.parent / "data" / "media_insights_cache.duckdb"

        self.cache_db_path = Path(cache_db_path)
        self.cache_db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = self._safe_connect()
        self._initialize_schema()

    def _safe_connect(self) -> duckdb.DuckDBPyConnection:
        """Connect to DuckDB, recovering gracefully from a corrupted WAL file."""
        config = {"enable_external_access": False}
        try:
            return duckdb.connect(str(self.cache_db_path), config=config)
        except duckdb.Error as exc:
            wal_path = self.cache_db_path.with_suffix(self.cache_db_path.suffix + ".wal")
            if "WAL" in str(exc) and wal_path.exists():
                logger.warning(
                    f"Corrupted WAL file detected ({wal_path}). Deleting and reconnecting."
                )
                wal_path.unlink()
                return duckdb.connect(str(self.cache_db_path), config=config)
            raise

    def _initialize_schema(self):
        """Create cache table if it doesn't exist."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS media_search_cache (
                query_hash     VARCHAR PRIMARY KEY,
                results_hash   VARCHAR NOT NULL,
                cached_results JSON NOT NULL,
                hit_count      INTEGER DEFAULT 1,
                created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Index for results_hash to quickly see if a specific state was ever cached
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_media_results_hash
            ON media_search_cache(results_hash)
        """)

        self.conn.commit()
        logger.info(f"Media insights cache initialized at {self.cache_db_path}")

    def generate_query_hash(self, params: dict) -> str:
        """Generate a stable hash for search parameters."""
        # Deep copy and sort any lists to ensure stability
        stable_params = {}
        for k, v in params.items():
            if isinstance(v, list):
                stable_params[k] = sorted(v)
            else:
                stable_params[k] = v

        # Sort keys to ensure stability
        normalized = json.dumps(stable_params, sort_keys=True, default=str)
        return hashlib.sha256(normalized.encode()).hexdigest()

    def generate_results_hash(self, hits: List[PodcastSearchHit]) -> str:
        """Generate a hash based on the current search results (IDs).

        This detects if the underlying data returned by the DB for a query has changed.
        """
        # We use segment_ids in order as they represent the Stage 1 "state"
        ids = [hit.segment_id for hit in hits]
        return hashlib.sha256(",".join(ids).encode()).hexdigest()

    def get_cached_results(self, query_hash: str) -> Optional[MediaCacheHit]:
        """Retrieve cached results for a query hash."""
        try:
            result = self.conn.execute(
                """
                SELECT cached_results, results_hash, created_at
                FROM media_search_cache
                WHERE query_hash = ?
                """,
                [query_hash],
            ).fetchone()

            if result:
                results_json, results_hash, created_at = result

                # Check expiration
                # created_at from DuckDB is often a naive datetime
                dt = created_at
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)

                if (datetime.now(timezone.utc) - dt).days > 7:
                    logger.info(f"Cache expired for query_hash: {query_hash[:8]}")
                    return None

                # Update usage stats
                self.conn.execute(
                    """
                    UPDATE media_search_cache
                    SET hit_count = hit_count + 1,
                        last_accessed = CURRENT_TIMESTAMP
                    WHERE query_hash = ?
                    """,
                    [query_hash],
                )
                self.conn.commit()

                # results_json is '[]' if no hits were cached
                hits = hits_adapter.validate_json(results_json)
                return MediaCacheHit(
                    hits=hits,
                    query_hash=query_hash,
                    results_hash=results_hash,
                    created_at=created_at,
                )
            return None
        except Exception as e:
            logger.error(f"Error retrieving media cache: {e}")
            return None

    def get_cached_results_by_data(self, results_hash: str) -> Optional[List[PodcastSearchHit]]:
        """Retrieve results if ANY query resulted in this same data state.

        This allows reusing AI reranking results even if the query string or
        filters changed slightly (e.g. parameter order), as long as the
        underlying database hits (Stage 1) are identical.
        """
        try:
            result = self.conn.execute(
                """
                SELECT cached_results
                FROM media_search_cache
                WHERE results_hash = ?
                LIMIT 1
                """,
                [results_hash],
            ).fetchone()

            if result:
                return hits_adapter.validate_json(result[0])
            return None
        except Exception as e:
            logger.error(f"Error retrieving media cache by data hash: {e}")
            return None

    def cache_results(
        self, query_hash: str, results_hash: str, hits: List[PodcastSearchHit]
    ):
        """Store results in the cache."""
        try:
            results_json = hits_adapter.dump_json(hits).decode()
            self.conn.execute(
                """
                INSERT OR REPLACE INTO media_search_cache
                (query_hash, results_hash, cached_results, created_at, last_accessed)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                [query_hash, results_hash, results_json],
            )
            self.conn.commit()
            logger.info(f"Cached media results for query_hash: {query_hash[:8]}...")
        except Exception as e:
            logger.error(f"Error caching media results: {e}")

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
