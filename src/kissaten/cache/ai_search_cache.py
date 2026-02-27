"""DuckDB-based cache for AI search query translations."""

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import duckdb

from ..schemas.ai_search import SearchParameters

logger = logging.getLogger(__name__)


@dataclass
class CacheHit:
    """Result of a successful cache lookup, bundling params with their unique entry identifier.

    ``entry_id`` identifies the *specific version* of the cached result (not just the query)
    and should be used as the opaque handle for submitting feedback.
    """

    search_params: SearchParameters
    entry_id: str


class AISearchCache:
    """Cache for AI search query translations using DuckDB."""

    def __init__(self, cache_db_path: str | Path = "data/ai_search_cache.duckdb"):
        """Initialize the AI search cache.

        Args:
            cache_db_path: Path to the DuckDB cache database file
        """
        self.cache_db_path = Path(cache_db_path)
        self.cache_db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = self._safe_connect()
        self._initialize_schema()

    def _safe_connect(self) -> duckdb.DuckDBPyConnection:
        """Connect to DuckDB, recovering gracefully from a corrupted WAL file.

        If the WAL file causes a replay error (e.g. from a previous failed
        migration that tried to load a blocked extension), delete it and
        reconnect so we start from the last committed checkpoint.
        """
        config = {"enable_external_access": False}
        try:
            return duckdb.connect(str(self.cache_db_path), config=config)
        except duckdb.Error as exc:
            wal_path = self.cache_db_path.with_suffix(self.cache_db_path.suffix + ".wal")
            if "WAL" in str(exc) and wal_path.exists():
                logger.warning(
                    f"Corrupted WAL file detected ({wal_path}). "
                    "Deleting it and reconnecting from last checkpoint. "
                    "Any uncommitted operations in the WAL will be lost."
                )
                wal_path.unlink()
                return duckdb.connect(str(self.cache_db_path), config=config)
            raise

    def _initialize_schema(self):
        """Create cache table if it doesn't exist."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS ai_query_cache (
                entry_id       VARCHAR PRIMARY KEY,
                query_hash     VARCHAR NOT NULL,
                version        INTEGER NOT NULL DEFAULT 1,
                query_type     VARCHAR NOT NULL,
                original_query TEXT,
                search_params  JSON NOT NULL,
                hit_count      INTEGER DEFAULT 1,
                created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at     TIMESTAMP NOT NULL,
                thumbs_up      INTEGER DEFAULT 0,
                thumbs_down    INTEGER DEFAULT 0
            )
        """)

        # Indexes
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_query_hash
            ON ai_query_cache(query_hash)
        """)

        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_expires_at
            ON ai_query_cache(expires_at)
        """)

        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_last_accessed
            ON ai_query_cache(last_accessed)
        """)

        # Rate limiting: track fresh (non-cached) AI requests
        self.conn.execute("""
            CREATE SEQUENCE IF NOT EXISTS fresh_request_log_id_seq
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS fresh_request_log (
                id INTEGER DEFAULT nextval('fresh_request_log_id_seq'),
                query_type VARCHAR NOT NULL,
                request_time TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_fresh_request_time
            ON fresh_request_log(request_time)
        """)

        self.conn.commit()
        logger.info(f"AI search cache initialized at {self.cache_db_path}")

    def _hash_text_query(self, query: str) -> str:
        """Generate hash for text query.

        Args:
            query: Natural language query string

        Returns:
            SHA256 hash of normalized query
        """
        # Normalize query: lowercase, strip whitespace, remove multiple spaces
        normalized = " ".join(query.lower().strip().split())
        return hashlib.sha256(normalized.encode()).hexdigest()

    def _hash_image_query(self, image_data: bytes) -> str:
        """Generate hash for image query.

        Args:
            image_data: Raw image bytes

        Returns:
            SHA256 hash of image data
        """
        return hashlib.sha256(image_data).hexdigest()

    def get_cached_query(
        self, query: str | None = None, image_data: bytes | None = None
    ) -> "CacheHit | None":
        """Retrieve the latest cached entry for a query.

        Returns the highest-version entry for the given query content hash.
        The returned :class:`CacheHit` contains both the search parameters and
        the ``entry_id`` that uniquely identifies this specific result version
        (suitable for submitting feedback or checking negative-rating status).

        Args:
            query: Text query (for text-based searches)
            image_data: Image bytes (for image-based searches)

        Returns:
            :class:`CacheHit` if an entry exists, ``None`` on a cache miss.
        """
        if query is None and image_data is None:
            raise ValueError("Either query or image_data must be provided")

        if query:
            query_hash = self._hash_text_query(query)
            query_type = "text"
        else:
            query_hash = self._hash_image_query(image_data)  # type: ignore
            query_type = "image"

        try:
            # Always return the latest version for this query_hash
            result = self.conn.execute(
                """
                SELECT entry_id, search_params, hit_count
                FROM ai_query_cache
                WHERE query_hash = ?
                ORDER BY version DESC
                LIMIT 1
                """,
                [query_hash],
            ).fetchone()

            if result:
                entry_id, search_params_json, hit_count = result

                # Update hit count and last accessed time on the specific version
                self.conn.execute(
                    """
                    UPDATE ai_query_cache
                    SET hit_count = hit_count + 1,
                        last_accessed = CURRENT_TIMESTAMP
                    WHERE entry_id = ?
                    """,
                    [entry_id],
                )
                self.conn.commit()

                logger.info(
                    f"Cache HIT for {query_type} query (hash: {query_hash[:8]}..., "
                    f"entry_id: {entry_id[:8]}..., hit_count: {hit_count + 1})"
                )

                params_dict = json.loads(search_params_json)
                return CacheHit(
                    search_params=SearchParameters(**params_dict),
                    entry_id=entry_id,
                )

            logger.info(f"Cache MISS for {query_type} query (hash: {query_hash[:8]}...)")
            return None

        except Exception as e:
            logger.error(f"Error retrieving cached query: {e}")
            return None

    def cache_query(
        self,
        search_params: SearchParameters,
        query: str | None = None,
        image_data: bytes | None = None,
        force_new_version: bool = False,
    ) -> str:
        """Cache search parameters for a query. Entries are stored indefinitely.

        Args:
            search_params: The SearchParameters to cache.
            query: Text query (for text-based searches).
            image_data: Image bytes (for image-based searches).
            force_new_version: When ``True``, always insert a *new* versioned
                entry rather than upserting the existing one.  Pass ``True``
                when re-running the AI after a negatively-rated cache bypass so
                the previous entry (and its vote history) is preserved.

        Returns:
            The ``entry_id`` of the stored (or newly created) entry.
        """
        if query is None and image_data is None:
            raise ValueError("Either query or image_data must be provided")

        if query:
            query_hash = self._hash_text_query(query)
            query_type = "text"
            original_query = query
        else:
            query_hash = self._hash_image_query(image_data)  # type: ignore
            query_type = "image"
            original_query = None

        try:
            search_params_json = search_params.model_dump_json()

            if force_new_version:
                # Find the current maximum version so we can increment it
                row = self.conn.execute(
                    "SELECT MAX(version) FROM ai_query_cache WHERE query_hash = ?",
                    [query_hash],
                ).fetchone()
                current_max = row[0] if row and row[0] is not None else 0
                new_version = current_max + 1
                entry_id = f"{query_hash}:v{new_version}"
            else:
                new_version = 1
                entry_id = query_hash

            # expires_at set far in the future — entries are effectively permanent
            self.conn.execute(
                """
                INSERT OR REPLACE INTO ai_query_cache
                (entry_id, query_hash, version, query_type, original_query, search_params,
                 expires_at, created_at, last_accessed)
                VALUES (?, ?, ?, ?, ?, ?, '9999-12-31 00:00:00', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                [entry_id, query_hash, new_version, query_type, original_query, search_params_json],
            )
            self.conn.commit()

            logger.info(
                f"Cached {query_type} query (entry_id: {entry_id[:8]}..., version: {new_version})"
            )
            return entry_id

        except Exception as e:
            logger.error(f"Error caching query: {e}")
            return query_hash  # fall back to base hash so callers always receive a string

    def check_rate_limit(self, window_hours: int = 24, max_requests: int = 10) -> dict:
        """Check if fresh AI requests are within the global rate limit.

        Args:
            window_hours: Rolling time window in hours
            max_requests: Maximum number of fresh requests allowed in the window

        Returns:
            Dict with 'allowed' (bool), 'remaining' (int), 'limit' (int),
            'reset_at' (datetime | None), 'window_hours' (int), 'current_count' (int)
        """
        try:
            window_start = datetime.now(timezone.utc) - timedelta(hours=window_hours)

            row = self.conn.execute(
                "SELECT COUNT(*) FROM fresh_request_log WHERE request_time >= ?",
                [window_start],
            ).fetchone()
            count = row[0] if row else 0

            remaining = max(0, max_requests - count)
            allowed = count < max_requests

            # Reset time: when the oldest request in the window expires
            if count >= max_requests:
                oldest = self.conn.execute(
                    """
                    SELECT MIN(request_time) FROM fresh_request_log
                    WHERE request_time >= ?
                    """,
                    [window_start],
                ).fetchone()
                if oldest and oldest[0]:
                    oldest_time = oldest[0]
                    if not oldest_time.tzinfo:
                        oldest_time = oldest_time.replace(tzinfo=timezone.utc)
                    reset_at = oldest_time + timedelta(hours=window_hours)
                else:
                    reset_at = datetime.now(timezone.utc) + timedelta(hours=window_hours)
            else:
                reset_at = None

            return {
                "allowed": allowed,
                "remaining": remaining,
                "limit": max_requests,
                "reset_at": reset_at,
                "window_hours": window_hours,
                "current_count": count,
            }

        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            # Fail open — allow the request if rate limit check errors
            return {
                "allowed": True,
                "remaining": max_requests,
                "limit": max_requests,
                "reset_at": None,
                "window_hours": window_hours,
                "current_count": 0,
            }

    def log_fresh_request(self, query_type: str) -> None:
        """Log a fresh (non-cached) AI request for rate limiting.

        Args:
            query_type: Type of request — 'text' or 'image'
        """
        try:
            self.conn.execute(
                "INSERT INTO fresh_request_log (query_type) VALUES (?)",
                [query_type],
            )
            self.conn.commit()
            logger.info(f"Logged fresh {query_type} AI request")
        except Exception as e:
            logger.error(f"Error logging fresh request: {e}")

    def submit_feedback(self, query_hash: str, vote: str) -> dict[str, int] | None:
        """Record a thumbs-up or thumbs-down vote for a cached search result.

        Args:
            query_hash: The entry_id identifying the cache entry
            vote: 'up' or 'down'

        Returns:
            Dict with updated thumbs_up and thumbs_down counts, or None if not found
        """
        if vote not in ("up", "down"):
            raise ValueError("vote must be 'up' or 'down'")

        column = "thumbs_up" if vote == "up" else "thumbs_down"
        try:
            self.conn.execute(
                f"UPDATE ai_query_cache SET {column} = {column} + 1 WHERE entry_id = ?",
                [query_hash],
            )
            row = self.conn.execute(
                "SELECT thumbs_up, thumbs_down FROM ai_query_cache WHERE entry_id = ?",
                [query_hash],
            ).fetchone()
            if row is None:
                return None
            self.conn.commit()
            logger.info(f"Recorded '{vote}' feedback for cache entry {query_hash[:8]}...")
            return {"thumbs_up": row[0], "thumbs_down": row[1]}
        except Exception as e:
            logger.error(f"Error submitting feedback: {e}")
            return None

    def is_negatively_rated(self, query_hash: str, threshold: int) -> bool:
        """Check whether a cache entry has accumulated too many downvotes.

        Args:
            query_hash: The entry_id identifying the cache entry
            threshold: Number of downvotes at or above which the entry is
                       considered negatively rated

        Returns:
            True if thumbs_down >= threshold, False otherwise (including when
            the entry does not exist or the check fails)
        """
        try:
            row = self.conn.execute(
                "SELECT thumbs_down FROM ai_query_cache WHERE entry_id = ?",
                [query_hash],
            ).fetchone()
            if row is None:
                return False
            return row[0] >= threshold
        except Exception as e:
            logger.error(f"Error checking negative rating: {e}")
            return False

    def cleanup_expired(self) -> int:
        """No-op: cache entries are now stored indefinitely.

        Returns:
            Always 0 — no entries expire.
        """
        return 0

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        try:
            stats = {}

            # Total cached queries
            row = self.conn.execute("SELECT COUNT(*) FROM ai_query_cache").fetchone()
            total = row[0] if row else 0
            stats["total_cached_queries"] = total

            # Count by type
            type_counts = self.conn.execute(
                """
                SELECT query_type, COUNT(*)
                FROM ai_query_cache
                GROUP BY query_type
                """
            ).fetchall()
            stats["by_type"] = {query_type: count for query_type, count in type_counts}

            # Top queries by hit count
            top_queries = self.conn.execute(
                """
                SELECT original_query, hit_count, query_type
                FROM ai_query_cache
                WHERE original_query IS NOT NULL
                ORDER BY hit_count DESC
                LIMIT 10
                """
            ).fetchall()
            stats["top_queries"] = [
                {"query": q, "hits": hits, "type": qtype} for q, hits, qtype in top_queries
            ]

            # Total hits
            row = self.conn.execute("SELECT SUM(hit_count) FROM ai_query_cache").fetchone()
            total_hits = row[0] if row else 0
            stats["total_hits"] = total_hits or 0

            # Cache hit rate (hits / total queries)
            if total > 0:
                stats["hit_rate"] = (total_hits - total) / total_hits if total_hits > 0 else 0
            else:
                stats["hit_rate"] = 0

            # Rate limit info
            rl = self.check_rate_limit()
            stats["rate_limit"] = {
                "current_count_24h": rl["current_count"],
                "limit": rl["limit"],
                "remaining": rl["remaining"],
                "window_hours": rl["window_hours"],
            }

            return stats

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {}

    def clear_cache(self, query_type: str | None = None) -> int:
        """Clear cache entries (actually delete them from database).

        Note: This is the only method that actually deletes entries.
        cleanup_expired() only counts expired entries without deleting.

        Args:
            query_type: If provided, only clear entries of this type ('text' or 'image')

        Returns:
            Number of entries cleared
        """
        try:
            if query_type:
                result = self.conn.execute(
                    "DELETE FROM ai_query_cache WHERE query_type = ?", [query_type]
                )
            else:
                result = self.conn.execute("DELETE FROM ai_query_cache")

            row = result.fetchone()
            deleted_count = row[0] if row else 0
            self.conn.commit()

            logger.info(f"Cleared {deleted_count} cache entries" + (f" ({query_type})" if query_type else ""))
            return deleted_count

        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return 0

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            logger.info("AI search cache connection closed")
