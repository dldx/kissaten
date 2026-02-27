"""Tests for AI search cache functionality."""

import hashlib
from pathlib import Path

import pytest

from kissaten.cache.ai_search_cache import AISearchCache
from kissaten.schemas.ai_search import SearchParameters


@pytest.fixture
def cache_db_path(tmp_path):
    """Provide a temporary cache database path."""
    return tmp_path / "test_cache.duckdb"


@pytest.fixture
def cache(cache_db_path):
    """Provide an AISearchCache instance."""
    cache_instance = AISearchCache(cache_db_path)
    yield cache_instance
    cache_instance.close()


def test_cache_initialization(cache_db_path):
    """Test that cache initializes correctly."""
    cache = AISearchCache(cache_db_path)

    # Check that database file was created
    assert cache_db_path.exists()

    # Check that tables exist
    result = cache.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='ai_query_cache'"
    ).fetchone()
    assert result is not None

    cache.close()


def test_text_query_caching(cache):
    """Test caching and retrieval of text queries."""
    query = "fruity Ethiopian coffee"
    search_params = SearchParameters(
        search_text="Ethiopian", tasting_notes_search="fruit*", origin=["ET"], confidence=0.9
    )

    # Cache the query
    cache.cache_query(search_params, query=query)

    # Retrieve from cache
    cache_hit = cache.get_cached_query(query=query)

    assert cache_hit is not None
    assert cache_hit.search_params.search_text == search_params.search_text
    assert cache_hit.search_params.tasting_notes_search == search_params.tasting_notes_search
    assert cache_hit.search_params.origin == search_params.origin
    assert cache_hit.search_params.confidence == search_params.confidence


def test_image_query_caching(cache):
    """Test caching and retrieval of image queries."""
    image_data = b"fake_image_data_12345"
    search_params = SearchParameters(
        search_text="Colombian",
        roast_level="Medium",
        confidence=0.85
    )

    # Cache the image query
    cache.cache_query(search_params, image_data=image_data)

    # Retrieve from cache
    cache_hit = cache.get_cached_query(image_data=image_data)

    assert cache_hit is not None
    assert cache_hit.search_params.search_text == search_params.search_text
    assert cache_hit.search_params.roast_level == search_params.roast_level
    assert cache_hit.search_params.confidence == search_params.confidence


def test_query_normalization(cache):
    """Test that queries are normalized for consistent cache hits."""
    search_params = SearchParameters(search_text="Ethiopian", confidence=0.9)

    # Cache with one form of the query
    cache.cache_query(search_params, query="  Ethiopian   Coffee  ")

    # Should find it with different spacing
    cached_params = cache.get_cached_query(query="Ethiopian Coffee")
    assert cached_params is not None

    # Should find it with different casing
    cached_params = cache.get_cached_query(query="ETHIOPIAN COFFEE")
    assert cached_params is not None


def test_cache_miss(cache):
    """Test that cache returns None for non-existent queries."""
    cached_params = cache.get_cached_query(query="non-existent query")
    assert cached_params is None


def test_hit_count_increment(cache):
    """Test that hit count increments on cache hits."""
    query = "test query"
    search_params = SearchParameters(confidence=0.9)

    cache.cache_query(search_params, query=query)

    # First hit
    cache.get_cached_query(query=query)

    # Second hit
    cache.get_cached_query(query=query)

    # Check hit count
    result = cache.conn.execute(
        "SELECT hit_count FROM ai_query_cache WHERE original_query = ?",
        [query]
    ).fetchone()

    assert result is not None
    assert result[0] == 3  # 1 initial + 2 hits


def test_new_version_on_negative_bypass(cache):
    """Test that force_new_version=True accumulates a new entry without replacing the old one."""
    query = "fruity Ethiopian coffee"
    params_v1 = SearchParameters(search_text="Ethiopian", confidence=0.9)
    params_v2 = SearchParameters(
        search_text="Ethiopian", tasting_notes_search="fruit*", confidence=0.95
    )

    # Store the initial (v1) result
    entry_id_v1 = cache.cache_query(params_v1, query=query)
    assert entry_id_v1 is not None

    # Simulate a negative-vote bypass: store a new version
    entry_id_v2 = cache.cache_query(params_v2, query=query, force_new_version=True)
    assert entry_id_v2 is not None
    assert entry_id_v2 != entry_id_v1

    # get_cached_query must return the latest version (v2)
    cache_hit = cache.get_cached_query(query=query)
    assert cache_hit is not None
    assert cache_hit.entry_id == entry_id_v2
    assert cache_hit.search_params.confidence == 0.95

    # Both entries must still exist in the database
    count = cache.conn.execute(
        "SELECT COUNT(*) FROM ai_query_cache WHERE original_query = ?",
        [query],
    ).fetchone()[0]
    assert count == 2

    # Old entry is preserved and identifiable by its own entry_id
    old_row = cache.conn.execute(
        "SELECT entry_id, version FROM ai_query_cache WHERE entry_id = ?",
        [entry_id_v1],
    ).fetchone()
    assert old_row is not None
    assert old_row[1] == 1  # version column

    new_row = cache.conn.execute(
        "SELECT entry_id, version FROM ai_query_cache WHERE entry_id = ?",
        [entry_id_v2],
    ).fetchone()
    assert new_row is not None
    assert new_row[1] == 2  # version column


def test_cleanup_expired(cache):
    """cleanup_expired is a no-op (entries are permanent); verify it returns 0."""
    search_params = SearchParameters(confidence=0.9)
    cache.cache_query(search_params, query="some query")

    expired_count = cache.cleanup_expired()
    assert expired_count == 0


def test_cache_stats(cache):
    """Test cache statistics retrieval."""
    # Add some test data
    text_params = SearchParameters(confidence=0.9)
    image_data = b"test_image"

    cache.cache_query(text_params, query="query 1")
    cache.cache_query(text_params, query="query 2")
    cache.cache_query(text_params, image_data=image_data)

    # Generate some hits
    cache.get_cached_query(query="query 1")
    cache.get_cached_query(query="query 1")

    stats = cache.get_cache_stats()

    assert stats["total_cached_queries"] == 3
    assert stats["by_type"]["text"] == 2
    assert stats["by_type"]["image"] == 1
    assert stats["total_hits"] > 3  # Initial + hits


def test_clear_cache(cache):
    """Test clearing cache entries."""
    text_params = SearchParameters(confidence=0.9)
    image_data = b"test_image"

    cache.cache_query(text_params, query="text query")
    cache.cache_query(text_params, image_data=image_data)

    # Clear only text queries
    deleted = cache.clear_cache(query_type="text")
    assert deleted == 1

    # Image query should still exist
    cached = cache.get_cached_query(image_data=image_data)
    assert cached is not None

    # Clear all
    deleted = cache.clear_cache()
    assert deleted == 1


def test_hash_consistency(cache):
    """Test that query hashing is consistent."""
    query1 = "Ethiopian Coffee"
    query2 = "  ethiopian   coffee  "

    hash1 = cache._hash_text_query(query1)
    hash2 = cache._hash_text_query(query2)

    # Normalized queries should have same hash
    assert hash1 == hash2


def test_image_hash_consistency(cache):
    """Test that image hashing is consistent."""
    image_data = b"test_image_data"

    hash1 = cache._hash_image_query(image_data)
    hash2 = cache._hash_image_query(image_data)

    # Same image data should have same hash
    assert hash1 == hash2

    # Different image data should have different hash
    different_data = b"different_image"
    hash3 = cache._hash_image_query(different_data)
    assert hash1 != hash3


def test_cache_with_all_search_params(cache):
    """Test caching with complex search parameters."""
    query = "complex search"
    search_params = SearchParameters(
        search_text="Ethiopian",
        tasting_notes_search="fruit*&berry*",
        roaster=["Cartwheel Coffee"],
        roaster_location=["GB"],
        origin=["ET"],
        region="Yirgacheffe",
        producer="Test Producer",
        farm="Test Farm",
        roast_level="Light",
        roast_profile="Filter",
        process="Washed",
        variety="Heirloom",
        min_price=10.0,
        max_price=25.0,
        min_weight=200,
        max_weight=500,
        min_elevation=1800,
        max_elevation=2200,
        in_stock_only=True,
        is_decaf=False,
        is_single_origin=True,
        use_tasting_notes_only=False,
        confidence=0.95,
    )

    # Cache the complex query
    cache.cache_query(search_params, query=query)

    # Retrieve and verify all fields
    cache_hit = cache.get_cached_query(query=query)

    assert cache_hit is not None
    assert cache_hit.search_params.search_text == search_params.search_text
    assert cache_hit.search_params.tasting_notes_search == search_params.tasting_notes_search
    assert cache_hit.search_params.roaster == search_params.roaster
    assert cache_hit.search_params.origin == search_params.origin
    assert cache_hit.search_params.min_price == search_params.min_price
    assert cache_hit.search_params.is_single_origin == search_params.is_single_origin
    assert cache_hit.search_params.confidence == search_params.confidence
