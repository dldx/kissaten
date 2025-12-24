#!/usr/bin/env python3
"""
Comprehensive pytest tests for the search_coffee_beans endpoint in kissaten.api.main
Tests all search parameters, filtering, pagination, sorting, and edge cases
"""
import os
import sys
from pathlib import Path

# Set environment variable to ensure we're in test mode
os.environ["PYTEST_CURRENT_TEST"] = "test_search_coffee_beans.py"

# Add the src directory to the path so we can import kissaten modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from kissaten.api.db import conn, init_database, load_coffee_data
from kissaten.api.main import app


@pytest_asyncio.fixture
async def setup_database():
    """Fixture to initialize database and clean up data before each test"""
    await init_database()

    # Clear existing data including static tables that get repopulated during load_coffee_data
    # Use TRUNCATE to reset auto-increment sequences
    conn.execute("TRUNCATE TABLE origins")
    conn.execute("TRUNCATE TABLE coffee_beans")
    conn.execute("TRUNCATE TABLE roasters")
    conn.execute("TRUNCATE TABLE country_codes")
    conn.execute("TRUNCATE TABLE roaster_location_codes")
    conn.execute("TRUNCATE TABLE tasting_notes_categories")
    conn.execute("TRUNCATE TABLE processed_files")
    conn.commit()

    yield

    # Cleanup after test
    conn.execute("TRUNCATE TABLE origins")
    conn.execute("TRUNCATE TABLE coffee_beans")
    conn.execute("TRUNCATE TABLE roasters")
    conn.execute("TRUNCATE TABLE country_codes")
    conn.execute("TRUNCATE TABLE roaster_location_codes")
    conn.execute("TRUNCATE TABLE tasting_notes_categories")
    conn.execute("TRUNCATE TABLE processed_files")
    conn.commit()


@pytest.fixture
def test_data_dir():
    """Fixture to provide test data directory path"""
    test_dir = Path(__file__).parent.parent / "test_data" / "roasters"
    if not test_dir.exists():
        pytest.skip(f"Test data directory not found: {test_dir}")
    return test_dir


@pytest.fixture
def client():
    """Fixture to provide FastAPI test client"""
    return TestClient(app)


# Basic Functionality Tests

@pytest.mark.asyncio
async def test_search_coffee_beans_no_parameters(setup_database, test_data_dir, client):
    """Test search endpoint without any parameters returns all beans"""
    await load_coffee_data(test_data_dir)

    response = client.get("/v1/search")

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "data" in data
    assert isinstance(data["data"], list)
    assert "pagination" in data
    assert "metadata" in data

    # Should have some results
    assert len(data["data"]) > 0


@pytest.mark.asyncio
async def test_search_coffee_beans_with_query(setup_database, test_data_dir, client):
    """Test search with general query parameter"""
    await load_coffee_data(test_data_dir)

    # Test with a specific term that should appear in results
    response = client.get("/v1/search?query=ethiopia")

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert isinstance(data["data"], list)

    # If we have results, they should be relevant to "ethiopia"
    if data["data"]:
        found_match = False
        for bean in data["data"]:
            bean_text = f"{bean['name']} {bean.get('description', '')}".lower()
            # Handle tasting notes which can be a list of strings or objects
            tasting_notes = bean.get('tasting_notes', [])
            if isinstance(tasting_notes, list):
                tasting_notes_text = " ".join([
                    str(note.get('note', '')) if isinstance(note, dict) else str(note)
                    for note in tasting_notes
                ])
            else:
                tasting_notes_text = ""

            # Check if "ethiopia" appears in name, description, or tasting notes
            if "ethiopia" in bean_text or "ethiopia" in tasting_notes_text.lower():
                found_match = True
                break

            # Also check origins for country match
            for origin in bean.get('origins', []):
                if origin.get('country_full_name', '').lower() == 'ethiopia' or origin.get('country', '').upper() == 'ET':
                    found_match = True
                    break

        # At least one result should match the search term
        assert found_match, f"No results matched 'ethiopia' in {len(data['data'])} results"


@pytest.mark.asyncio
async def test_search_coffee_beans_with_tasting_notes_query(setup_database, test_data_dir, client):
    """Test search with tasting_notes_query parameter"""
    await load_coffee_data(test_data_dir)

    # Test with wildcard search for fruity notes
    response = client.get("/v1/search?tasting_notes_query=fruit*")

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert isinstance(data["data"], list)

    # If we have results, they should contain fruity tasting notes
    if data["data"]:
        found_fruity_match = False
        for bean in data["data"]:
            tasting_notes = bean.get('tasting_notes', [])
            if isinstance(tasting_notes, list):
                tasting_notes_text = " ".join([
                    str(note.get('note', '')) if isinstance(note, dict) else str(note)
                    for note in tasting_notes
                ]).lower()

                # Check for fruit-related terms
                fruit_terms = ['fruit', 'fruity', 'berry', 'apple', 'citrus', 'orange', 'lemon', 'cherry', 'grape']
                if any(term in tasting_notes_text for term in fruit_terms):
                    found_fruity_match = True
                    break

        # At least one result should have fruity tasting notes
        assert found_fruity_match, f"No results contained fruity tasting notes in {len(data['data'])} results"


@pytest.mark.asyncio
async def test_search_coffee_beans_with_boolean_tasting_notes_query(setup_database, test_data_dir, client):
    """Test search with boolean operators in tasting_notes_query"""
    await load_coffee_data(test_data_dir)

    # Test with boolean AND operator - look for beans with both chocolate AND berry notes
    response = client.get("/v1/search?tasting_notes_query=chocolate&berry")

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert isinstance(data["data"], list)

    # If we have results, they should contain both chocolate AND berry in tasting notes
    if data["data"]:
        found_both_match = False
        for bean in data["data"]:
            tasting_notes = bean.get('tasting_notes', [])
            if isinstance(tasting_notes, list):
                tasting_notes_text = " ".join([
                    str(note.get('note', '')) if isinstance(note, dict) else str(note)
                    for note in tasting_notes
                ]).lower()

                # Check for both chocolate and berry terms
                has_chocolate = any(term in tasting_notes_text for term in ['chocolate', 'cocoa', 'cacao'])
                has_berry = any(term in tasting_notes_text for term in ['berry', 'berries', 'blueberry', 'strawberry', 'raspberry'])

                if has_chocolate and has_berry:
                    found_both_match = True
                    break

        # At least one result should have both chocolate and berry notes
        assert found_both_match, f"No results contained both chocolate AND berry tasting notes in {len(data['data'])} results"


# Filter Tests

@pytest.mark.asyncio
async def test_search_coffee_beans_with_roaster_filter(setup_database, test_data_dir, client):
    """Test search with roaster filter"""
    await load_coffee_data(test_data_dir)

    # Get available roasters
    roasters_result = conn.execute("SELECT DISTINCT roaster FROM coffee_beans LIMIT 1").fetchall()
    if not roasters_result:
        pytest.skip("No roasters found in test data")

    test_roaster = roasters_result[0][0]

    response = client.get(f"/v1/search?roaster={test_roaster}")

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert isinstance(data["data"], list)

    # All results should be from the specified roaster
    for bean in data["data"]:
        assert bean["roaster"] == test_roaster


@pytest.mark.asyncio
async def test_search_coffee_beans_with_multiple_roasters(setup_database, test_data_dir, client):
    """Test search with multiple roaster filters"""
    await load_coffee_data(test_data_dir)

    # Get available roasters
    roasters_result = conn.execute("SELECT DISTINCT roaster FROM coffee_beans LIMIT 2").fetchall()
    if len(roasters_result) < 2:
        pytest.skip("Need at least 2 roasters in test data")

    roaster1 = roasters_result[0][0]
    roaster2 = roasters_result[1][0]

    response = client.get(f"/v1/search?roaster={roaster1}&roaster={roaster2}")

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert isinstance(data["data"], list)

    # All results should be from one of the specified roasters
    valid_roasters = {roaster1, roaster2}
    for bean in data["data"]:
        assert bean["roaster"] in valid_roasters


@pytest.mark.asyncio
async def test_search_coffee_beans_with_origin_filter(setup_database, test_data_dir, client):
    """Test search with origin filter"""
    await load_coffee_data(test_data_dir)

    # Get available origins
    origins_result = conn.execute("SELECT DISTINCT country FROM origins LIMIT 1").fetchall()
    if not origins_result:
        pytest.skip("No origins found in test data")

    test_origin = origins_result[0][0]

    response = client.get(f"/v1/search?origin={test_origin}")

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert isinstance(data["data"], list)

    # If we have results, they should all be from the specified origin
    if data["data"]:
        for bean in data["data"]:
            found_origin_match = False
            for origin in bean.get('origins', []):
                if origin.get('country', '').upper() == test_origin.upper():
                    found_origin_match = True
                    break

            assert found_origin_match, f"Bean '{bean['name']}' does not have origin '{test_origin}'"


@pytest.mark.asyncio
async def test_search_coffee_beans_with_price_range(setup_database, test_data_dir, client):
    """Test search with price range filters"""
    await load_coffee_data(test_data_dir)

    response = client.get("/v1/search?min_price=10&max_price=50")

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert isinstance(data["data"], list)

    # Check that prices are within range (if price is available)
    for bean in data["data"]:
        if bean.get("price") is not None:
            assert 10 <= bean["price"] <= 50


@pytest.mark.asyncio
async def test_search_coffee_beans_with_weight_range(setup_database, test_data_dir, client):
    """Test search with weight range filters"""
    await load_coffee_data(test_data_dir)

    response = client.get("/v1/search?min_weight=200&max_weight=500")

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert isinstance(data["data"], list)

    # Check that weights are within range (if weight is available)
    for bean in data["data"]:
        if bean.get("weight") is not None:
            assert 200 <= bean["weight"] <= 500


@pytest.mark.asyncio
async def test_search_coffee_beans_with_boolean_filters(setup_database, test_data_dir, client):
    """Test search with boolean filters"""
    await load_coffee_data(test_data_dir)

    response = client.get("/v1/search?in_stock_only=true&is_single_origin=true")

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert isinstance(data["data"], list)

    # Check boolean filters
    for bean in data["data"]:
        if bean.get("in_stock") is not None:
            assert bean["in_stock"] is True
        if bean.get("is_single_origin") is not None:
            assert bean["is_single_origin"] is True


@pytest.mark.asyncio
async def test_search_coffee_beans_with_roast_level_filter(setup_database, test_data_dir, client):
    """Test search with roast level filter using wildcards"""
    await load_coffee_data(test_data_dir)

    response = client.get("/v1/search?roast_level=medium*")

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert isinstance(data["data"], list)

    # If we have results, they should all have medium roast levels
    if data["data"]:
        for bean in data["data"]:
            roast_level = bean.get('roast_level', '').lower()
            # Should match medium, medium-light, medium-dark, etc.
            assert roast_level.startswith('medium'), f"Bean '{bean['name']}' has roast level '{bean.get('roast_level')}' which doesn't start with 'medium'"


# Pagination Tests

@pytest.mark.asyncio
async def test_search_coffee_beans_pagination(setup_database, test_data_dir, client):
    """Test search pagination"""
    await load_coffee_data(test_data_dir)

    # Test first page
    response = client.get("/v1/search?page=1&per_page=5")

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert isinstance(data["data"], list)
    assert len(data["data"]) <= 5

    # Check pagination info
    pagination = data["pagination"]
    assert pagination["page"] == 1
    assert pagination["per_page"] == 5
    assert "total_items" in pagination
    assert "total_pages" in pagination
    assert "has_next" in pagination
    assert "has_previous" in pagination
    assert pagination["has_previous"] is False


@pytest.mark.asyncio
async def test_search_coffee_beans_pagination_second_page(setup_database, test_data_dir, client):
    """Test search pagination second page"""
    await load_coffee_data(test_data_dir)

    # Get total count first
    response_first = client.get("/v1/search?per_page=3")
    data_first = response_first.json()

    if data_first["pagination"]["total_pages"] > 1:
        # Test second page
        response = client.get("/v1/search?page=2&per_page=3")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert isinstance(data["data"], list)

        pagination = data["pagination"]
        assert pagination["page"] == 2
        assert pagination["has_previous"] is True


# Sorting Tests

@pytest.mark.asyncio
async def test_search_coffee_beans_sort_by_name(setup_database, test_data_dir, client):
    """Test search sorting by name"""
    await load_coffee_data(test_data_dir)

    response = client.get("/v1/search?sort_by=name&sort_order=asc&per_page=10")

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert isinstance(data["data"], list)

    # Check that results are sorted by name
    if len(data["data"]) > 1:
        names = [bean["name"] for bean in data["data"]]
        assert names == sorted(names)


@pytest.mark.asyncio
async def test_search_coffee_beans_sort_by_roaster(setup_database, test_data_dir, client):
    """Test search sorting by roaster"""
    await load_coffee_data(test_data_dir)

    response = client.get("/v1/search?sort_by=roaster&sort_order=asc&per_page=10")

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert isinstance(data["data"], list)

    # Check that results are sorted by roaster
    if len(data["data"]) > 1:
        roasters = [bean["roaster"] for bean in data["data"]]
        assert roasters == sorted(roasters)


@pytest.mark.asyncio
async def test_search_coffee_beans_sort_by_price(setup_database, test_data_dir, client):
    """Test search sorting by price with currency conversion"""
    await load_coffee_data(test_data_dir)

    # Test price sorting with currency conversion to USD to make validation easier
    response = client.get("/v1/search?sort_by=price&sort_order=asc&per_page=10&convert_to_currency=USD")

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert isinstance(data["data"], list)

    # With USD conversion, we can validate the sorting more reliably
    if len(data["data"]) > 1:
        prices_per_gram = []
        for bean in data["data"]:
            price = bean.get("price")  # Should be in USD due to conversion
            weight = bean.get("weight")
            currency = bean.get("currency")

            # Verify currency conversion worked
            if bean.get("price_converted"):
                assert currency == "USD", f"Expected USD currency for converted price, got {currency}"

            if price is not None and weight is not None and weight > 0:
                price_per_gram = price / weight
                prices_per_gram.append(price_per_gram)

        # Prices per gram should be in ascending order
        if len(prices_per_gram) > 1:
            # Allow for small floating point differences
            for i in range(1, len(prices_per_gram)):
                assert prices_per_gram[i] >= prices_per_gram[i-1] - 0.001, \
                    f"Prices per gram not in ascending order at index {i}: {prices_per_gram[i-1]:.4f} > {prices_per_gram[i]:.4f}"


@pytest.mark.asyncio
async def test_search_coffee_beans_sort_by_relevance(setup_database, test_data_dir, client):
    """Test search sorting by relevance (scoring mode)"""
    await load_coffee_data(test_data_dir)

    response = client.get("/v1/search?query=coffee&sort_by=relevance&per_page=10")

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert isinstance(data["data"], list)

    # In relevance mode, should have metadata about scoring
    metadata = data["metadata"]
    assert "max_possible_score" in metadata
    assert "search_query" in metadata


# Currency Conversion Tests

@pytest.mark.asyncio
async def test_search_coffee_beans_currency_conversion(setup_database, test_data_dir, client):
    """Test search with currency conversion"""
    await load_coffee_data(test_data_dir)

    # First get results without conversion
    response_original = client.get("/v1/search?per_page=5")
    original_data = response_original.json()

    # Then get results with EUR conversion
    response = client.get("/v1/search?convert_to_currency=EUR&per_page=5")

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert isinstance(data["data"], list)

    # Check currency conversion metadata
    metadata = data["metadata"]
    if "currency_conversion" in metadata:
        assert metadata["currency_conversion"]["enabled"] is True
        assert metadata["currency_conversion"]["target_currency"] == "EUR"

        # Check that some beans have been converted (if they had different original currency)
        converted_count = 0
        for bean in data["data"]:
            if bean.get("price_converted") is True:
                converted_count += 1
                # Converted beans should have EUR as currency
                assert bean.get("currency") == "EUR", f"Converted bean should have EUR currency, got {bean.get('currency')}"
                # Should have original price and currency fields
                assert "original_price" in bean
                assert "original_currency" in bean

        # Metadata should match the actual converted count
        assert metadata["currency_conversion"]["converted_results"] == converted_count


# Complex Filter Combinations

@pytest.mark.asyncio
async def test_search_coffee_beans_multiple_filters(setup_database, test_data_dir, client):
    """Test search with multiple filters combined"""
    await load_coffee_data(test_data_dir)

    # Get test data
    roasters_result = conn.execute("SELECT DISTINCT roaster FROM coffee_beans LIMIT 1").fetchall()
    origins_result = conn.execute("SELECT DISTINCT country FROM origins LIMIT 1").fetchall()

    if not roasters_result or not origins_result:
        pytest.skip("Insufficient test data for multiple filter test")

    test_roaster = roasters_result[0][0]
    test_origin = origins_result[0][0]

    response = client.get(
        f"/v1/search?roaster={test_roaster}&origin={test_origin}&in_stock_only=true&min_price=5"
    )

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert isinstance(data["data"], list)


# Error Handling Tests

@pytest.mark.asyncio
async def test_search_coffee_beans_invalid_page(setup_database, test_data_dir, client):
    """Test search with invalid page parameter"""
    await load_coffee_data(test_data_dir)

    response = client.get("/v1/search?page=0")

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_search_coffee_beans_invalid_per_page(setup_database, test_data_dir, client):
    """Test search with invalid per_page parameter"""
    await load_coffee_data(test_data_dir)

    response = client.get("/v1/search?per_page=200")  # Over limit

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_search_coffee_beans_invalid_sort_by(setup_database, test_data_dir, client):
    """Test search with invalid sort_by parameter"""
    await load_coffee_data(test_data_dir)

    response = client.get("/v1/search?sort_by=invalid_field")

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_search_coffee_beans_invalid_sort_order(setup_database, test_data_dir, client):
    """Test search with invalid sort_order parameter"""
    await load_coffee_data(test_data_dir)

    response = client.get("/v1/search?sort_order=invalid_order")

    assert response.status_code == 422  # Validation error


# Response Structure Tests

@pytest.mark.asyncio
async def test_search_coffee_beans_response_structure(setup_database, test_data_dir, client):
    """Test that search returns the expected response structure"""
    await load_coffee_data(test_data_dir)

    response = client.get("/v1/search?per_page=1")

    assert response.status_code == 200
    data = response.json()

    # Check top-level structure
    assert data["success"] is True
    assert "data" in data
    assert "pagination" in data
    assert "metadata" in data

    # Check pagination structure
    pagination = data["pagination"]
    assert "page" in pagination
    assert "per_page" in pagination
    assert "total_items" in pagination
    assert "total_pages" in pagination
    assert "has_next" in pagination
    assert "has_previous" in pagination

    # Check metadata structure
    metadata = data["metadata"]
    assert "total_results" in metadata
    assert "max_possible_score" in metadata

    # Check bean structure (if we have results)
    if data["data"]:
        bean = data["data"][0]
        required_fields = ["id", "name", "roaster", "url"]
        for field in required_fields:
            assert field in bean

        # Check that origins is a list
        assert "origins" in bean
        assert isinstance(bean["origins"], list)

        # Check that tasting_notes exists (can be empty list)
        assert "tasting_notes" in bean


# Performance Tests

@pytest.mark.asyncio
async def test_search_coffee_beans_empty_results(setup_database, test_data_dir, client):
    """Test search that returns no results"""
    await load_coffee_data(test_data_dir)

    # Search for something that definitely won't exist
    response = client.get("/v1/search?query=nonexistent_coffee_xyz123_definitely_not_found")

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert isinstance(data["data"], list)
    assert len(data["data"]) == 0

    # Pagination should still be valid for empty results
    pagination = data["pagination"]
    assert pagination["total_items"] == 0
    assert pagination["total_pages"] == 0
    assert pagination["page"] == 1
    assert pagination["has_next"] is False
    assert pagination["has_previous"] is False

    # Metadata should still be present
    metadata = data["metadata"]
    assert "total_results" in metadata
    assert metadata["total_results"] == 0


@pytest.mark.asyncio
async def test_search_coffee_beans_deprecated_tasting_notes_only(setup_database, test_data_dir, client):
    """Test deprecated tasting_notes_only parameter still works"""
    await load_coffee_data(test_data_dir)

    response = client.get("/v1/search?query=chocolate&tasting_notes_only=true")

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert isinstance(data["data"], list)


# Edge Cases

@pytest.mark.asyncio
async def test_search_coffee_beans_special_characters_in_query(setup_database, test_data_dir, client):
    """Test search with special characters in query"""
    await load_coffee_data(test_data_dir)

    response = client.get("/v1/search?query=caf%C3%A9")  # URL encoded café

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert isinstance(data["data"], list)


@pytest.mark.asyncio
async def test_search_coffee_beans_very_long_query(setup_database, test_data_dir, client):
    """Test search with very long query string"""
    await load_coffee_data(test_data_dir)

    long_query = "a" * 500  # Very long query
    response = client.get(f"/v1/search?query={long_query}")

    # Should handle gracefully (either return results or proper error)
    assert response.status_code in [200, 422]


@pytest.mark.asyncio
async def test_search_coffee_beans_random_sort_order(setup_database, test_data_dir, client):
    """Test search with random sort order"""
    await load_coffee_data(test_data_dir)

    response1 = client.get("/v1/search?sort_order=random&per_page=5")
    response2 = client.get("/v1/search?sort_order=random&per_page=5")

    assert response1.status_code == 200
    assert response2.status_code == 200

    data1 = response1.json()
    data2 = response2.json()

    assert data1["success"] is True
    assert data2["success"] is True

    # Results might be in different order (though not guaranteed with small datasets)
    assert isinstance(data1["data"], list)
    assert isinstance(data2["data"], list)
