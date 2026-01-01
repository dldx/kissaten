"""DuckDB-based cache for AI search query translations."""

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import duckdb

from ..schemas.ai_search import SearchParameters

logger = logging.getLogger(__name__)


class AISearchCache:
    """Cache for AI search query translations using DuckDB."""

    def __init__(self, cache_db_path: str | Path = "data/ai_search_cache.duckdb"):
        """Initialize the AI search cache.

        Args:
            cache_db_path: Path to the DuckDB cache database file
        """
        self.cache_db_path = Path(cache_db_path)
        self.cache_db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(str(self.cache_db_path))
        self._initialize_schema()

    def _initialize_schema(self):
        """Create cache table if it doesn't exist."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS ai_query_cache (
                query_hash VARCHAR PRIMARY KEY,
                query_type VARCHAR NOT NULL,  -- 'text' or 'image'
                original_query TEXT,  -- NULL for image queries
                search_params JSON NOT NULL,
                hit_count INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL
            )
        """)

        # Create indexes for faster lookups
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
    ) -> SearchParameters | None:
        """Retrieve cached search parameters for a query.

        Note: Expired entries (>7 days old) are not returned as cache hits,
        but are preserved in the database for dataset building purposes.

        Args:
            query: Text query (for text-based searches)
            image_data: Image bytes (for image-based searches)

        Returns:
            SearchParameters if found and not expired, None otherwise
        """
        if query is None and image_data is None:
            raise ValueError("Either query or image_data must be provided")

        # Generate hash based on query type
        if query:
            query_hash = self._hash_text_query(query)
            query_type = "text"
        else:
            query_hash = self._hash_image_query(image_data)  # type: ignore
            query_type = "image"

        try:
            # Check if cached entry exists and is not expired
            result = self.conn.execute(
                """
                SELECT search_params, hit_count
                FROM ai_query_cache
                WHERE query_hash = ?
                AND expires_at > CURRENT_TIMESTAMP
                """,
                [query_hash],
            ).fetchone()

            if result:
                search_params_json, hit_count = result

                # Update hit count and last accessed time
                self.conn.execute(
                    """
                    UPDATE ai_query_cache
                    SET hit_count = hit_count + 1,
                        last_accessed = CURRENT_TIMESTAMP
                    WHERE query_hash = ?
                    """,
                    [query_hash],
                )
                self.conn.commit()

                logger.info(
                    f"Cache HIT for {query_type} query (hash: {query_hash[:8]}..., "
                    f"hit_count: {hit_count + 1})"
                )

                # Parse JSON and return SearchParameters
                params_dict = json.loads(search_params_json)
                return SearchParameters(**params_dict)

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
        ttl_hours: int = 168,  # 7 days default
    ):
        """Cache search parameters for a query.

        Args:
            search_params: The SearchParameters to cache
            query: Text query (for text-based searches)
            image_data: Image bytes (for image-based searches)
            ttl_hours: Time-to-live in hours (default: 7 days)
        """
        if query is None and image_data is None:
            raise ValueError("Either query or image_data must be provided")

        # Generate hash based on query type
        if query:
            query_hash = self._hash_text_query(query)
            query_type = "text"
            original_query = query
        else:
            query_hash = self._hash_image_query(image_data)  # type: ignore
            query_type = "image"
            original_query = None

        try:
            # Calculate expiration time
            expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)

            # Serialize search parameters to JSON
            search_params_json = search_params.model_dump_json()

            # Insert or replace cached entry
            self.conn.execute(
                """
                INSERT OR REPLACE INTO ai_query_cache
                (query_hash, query_type, original_query, search_params, expires_at, created_at, last_accessed)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                [query_hash, query_type, original_query, search_params_json, expires_at],
            )
            self.conn.commit()

            logger.info(f"Cached {query_type} query (hash: {query_hash[:8]}..., ttl: {ttl_hours}h)")

        except Exception as e:
            logger.error(f"Error caching query: {e}")

    def cleanup_expired(self) -> int:
        """Count expired cache entries without deleting them.

        Note: Expired entries are preserved for dataset building purposes.
        They won't be returned as cache hits, but remain in the database
        for analytics and query pattern analysis.

        Returns:
            Number of expired entries (for informational purposes only)
        """
        try:
            # Count expired entries but don't delete them
            row = self.conn.execute(
                """
                SELECT COUNT(*) FROM ai_query_cache
                WHERE expires_at < CURRENT_TIMESTAMP
                """
            ).fetchone()
            expired_count = row[0] if row else 0

            if expired_count > 0:
                logger.info(
                    f"Found {expired_count} expired cache entries "
                    f"(preserved for dataset building)"
                )

            return expired_count

        except Exception as e:
            logger.error(f"Error counting expired entries: {e}")
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

            # Expired count
            row = self.conn.execute(
                "SELECT COUNT(*) FROM ai_query_cache WHERE expires_at < CURRENT_TIMESTAMP"
            ).fetchone()
            expired = row[0] if row else 0
            stats["expired_count"] = expired

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
