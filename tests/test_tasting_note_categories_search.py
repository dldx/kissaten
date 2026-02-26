#!/usr/bin/env python3
"""
Pytest tests for the tasting note categories search functionality in kissaten.api.main
Tests the get_tasting_note_categories() function with filtering parameters
"""
import pytest
from fastapi.testclient import TestClient

from kissaten.api.db import conn
from kissaten.api.main import app




@pytest.mark.asyncio
async def test_get_tasting_note_categories_no_filters(client):
    """Test that get_tasting_note_categories works without any filters"""
    # Load test data

    # Make request without filters
    response = client.get("/v1/tasting-note-categories")

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "data" in data
    assert "categories" in data["data"]
    assert "metadata" in data["data"]

    # Should have categories structure (may be empty if no tasting notes in test data)
    categories = data["data"]["categories"]
    assert isinstance(categories, dict)

    # Check metadata structure
    metadata = data["data"]["metadata"]
    assert "total_notes" in metadata
    assert "total_unique_descriptors" in metadata
    assert "total_primary_categories" in metadata


@pytest.mark.asyncio
async def test_get_tasting_note_categories_with_roaster_filter(client):
    """Test that get_tasting_note_categories works with roaster filter"""
    # Load test data

    # Get all categories first to see what roasters we have
    response_all = client.get("/v1/tasting-note-categories")
    assert response_all.status_code == 200

    # Get available roasters from the database
    roasters_result = conn.execute("SELECT DISTINCT roaster FROM coffee_beans LIMIT 1").fetchall()
    if not roasters_result:
        pytest.skip("No roasters found in test data")

    test_roaster = roasters_result[0][0]

    # Make request with roaster filter
    response = client.get(f"/v1/tasting-note-categories?roaster={test_roaster}")

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "data" in data
    assert "categories" in data["data"]

    # Should have categories (or empty if no tasting notes for this roaster)
    categories = data["data"]["categories"]
    # The result should be valid even if empty
    assert isinstance(categories, dict)


@pytest.mark.asyncio
async def test_get_tasting_note_categories_with_query_filter(client):
    """Test that get_tasting_note_categories works with general query filter"""
    # Load test data

    # Make request with a general query
    response = client.get("/v1/tasting-note-categories?query=coffee")

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "data" in data
    assert "categories" in data["data"]

    # Should return valid structure even if no matches
    categories = data["data"]["categories"]
    assert isinstance(categories, dict)


@pytest.mark.asyncio
async def test_get_tasting_note_categories_with_tasting_notes_query(client):
    """Test that get_tasting_note_categories works with tasting notes query filter"""
    # Load test data

    # Make request with tasting notes query using wildcard
    response = client.get("/v1/tasting-note-categories?tasting_notes_query=fruit*")

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "data" in data
    assert "categories" in data["data"]

    categories = data["data"]["categories"]
    assert isinstance(categories, dict)


@pytest.mark.asyncio
async def test_get_tasting_note_categories_with_origin_filter(client):
    """Test that get_tasting_note_categories works with origin filter"""
    # Load test data

    # Get available origins from the database
    origins_result = conn.execute("SELECT DISTINCT country FROM origins LIMIT 1").fetchall()
    if not origins_result:
        pytest.skip("No origins found in test data")

    test_origin = origins_result[0][0]

    # Make request with origin filter
    response = client.get(f"/v1/tasting-note-categories?origin={test_origin}")

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "data" in data
    assert "categories" in data["data"]

    categories = data["data"]["categories"]
    assert isinstance(categories, dict)


@pytest.mark.asyncio
async def test_get_tasting_note_categories_with_price_range(client):
    """Test that get_tasting_note_categories works with price range filters"""
    # Load test data

    # Make request with price range
    response = client.get("/v1/tasting-note-categories?min_price=10&max_price=50")

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "data" in data
    assert "categories" in data["data"]

    categories = data["data"]["categories"]
    assert isinstance(categories, dict)


@pytest.mark.asyncio
async def test_get_tasting_note_categories_with_boolean_filters(client):
    """Test that get_tasting_note_categories works with boolean filters"""
    # Load test data

    # Make request with boolean filters
    response = client.get("/v1/tasting-note-categories?in_stock_only=true&is_single_origin=true")

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "data" in data
    assert "categories" in data["data"]

    categories = data["data"]["categories"]
    assert isinstance(categories, dict)


@pytest.mark.asyncio
async def test_get_tasting_note_categories_with_multiple_filters(client):
    """Test that get_tasting_note_categories works with multiple filters combined"""
    # Load test data

    # Get a roaster and origin for testing
    roasters_result = conn.execute("SELECT DISTINCT roaster FROM coffee_beans LIMIT 1").fetchall()
    origins_result = conn.execute("SELECT DISTINCT country FROM origins LIMIT 1").fetchall()

    if not roasters_result or not origins_result:
        pytest.skip("Insufficient test data for multiple filter test")

    test_roaster = roasters_result[0][0]
    test_origin = origins_result[0][0]

    # Make request with multiple filters
    response = client.get(
        f"/v1/tasting-note-categories?roaster={test_roaster}&origin={test_origin}&in_stock_only=true"
    )

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "data" in data
    assert "categories" in data["data"]

    categories = data["data"]["categories"]
    assert isinstance(categories, dict)


@pytest.mark.asyncio
async def test_get_tasting_note_categories_with_currency_conversion(client):
    """Test that get_tasting_note_categories works with currency conversion"""
    # Load test data

    # Make request with currency conversion
    response = client.get("/v1/tasting-note-categories?convert_to_currency=EUR&min_price=10")

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "data" in data
    assert "categories" in data["data"]

    categories = data["data"]["categories"]
    assert isinstance(categories, dict)


@pytest.mark.asyncio
async def test_get_tasting_note_categories_response_structure(client):
    """Test that get_tasting_note_categories returns the expected response structure"""
    # Load test data

    response = client.get("/v1/tasting-note-categories")

    assert response.status_code == 200
    data = response.json()

    # Check top-level structure
    assert data["success"] is True
    assert "data" in data

    # Check data structure
    response_data = data["data"]
    assert "categories" in response_data
    assert "metadata" in response_data

    # Check metadata structure
    metadata = response_data["metadata"]
    assert "total_notes" in metadata
    assert "total_unique_descriptors" in metadata
    assert "total_primary_categories" in metadata
    assert isinstance(metadata["total_notes"], int)
    assert isinstance(metadata["total_unique_descriptors"], int)
    assert isinstance(metadata["total_primary_categories"], int)

    # Check categories structure
    categories = response_data["categories"]
    assert isinstance(categories, dict)

    # If we have categories, check their structure
    for primary_cat, secondary_cats in categories.items():
        assert isinstance(primary_cat, str)
        assert isinstance(secondary_cats, list)

        for category_info in secondary_cats:
            assert "primary_category" in category_info
            assert "secondary_category" in category_info
            assert "tertiary_category" in category_info
            assert "note_count" in category_info
            assert "bean_count" in category_info
            assert "tasting_notes" in category_info
            assert "tasting_notes_with_counts" in category_info

            assert isinstance(category_info["note_count"], int)
            assert isinstance(category_info["bean_count"], int)
            assert isinstance(category_info["tasting_notes"], list)
            assert isinstance(category_info["tasting_notes_with_counts"], list)
