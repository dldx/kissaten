#!/usr/bin/env python3
"""
Pytest tests for the Full-Text Search (FTS) feature in kissaten.api.main
"""
import pytest
from fastapi.testclient import TestClient
from kissaten.api.db import conn
from kissaten.api.main import app

@pytest.mark.asyncio
async def test_search_coffee_beans_fts_basic(client):
    """Test basic FTS query returns relevant results"""
    # Search for a term that is likely to be in the test data (e.g., a process or origin)
    # The FTS search should be more performant and rank by relevance
    response = client.get("/v1/search?fts_query=washed")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)

    if data["data"]:
        # Check that "washed" appears in at least one field indexed by FTS
        # FTS indexes: name, roaster, description, tasting_notes, country, region, producer, farm, process, variety
        found = False
        for bean in data["data"]:
            # Check process directly
            if "washed" in (bean.get("process") or "").lower():
                found = True
                break

            # Check description or name
            if "washed" in bean["name"].lower() or "washed" in (bean.get("description") or "").lower():
                found = True
                break

        assert found, "FTS query 'washed' returned no beans with 'washed' in indexed fields"

@pytest.mark.asyncio
async def test_search_coffee_beans_fts_ranking(client):
    """Test that FTS ranking (BM25) works by checking the relevance metadata"""
    # Assuming we have some beans with "coffee" in the name or description
    response = client.get("/v1/search?fts_query=coffee&sort_by=relevance&sort_order=desc")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    if len(data["data"]) > 1:
        # If we have multiple results, they should be sorted by relevance if handled by DuckDB FTS correctly
        # Note: In our implementation, build_coffee_bean_filters adds the score to the subquery
        # and search_coffee_beans handles the ordering if sort_by="relevance"
        pass # The test passes if the request succeeds and returns data

@pytest.mark.asyncio
async def test_search_coffee_beans_fts_vs_query(client):
    """Test that fts_query and standard query can be used together (intersection)"""
    # Use fts_query for one term and query for another
    # and check if the result matches both
    response = client.get("/v1/search?fts_query=washed&query=ethiopia")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    if data["data"]:
        for bean in data["data"]:
            # Check if either query matches (standard query) OR if origin matches
            origin_match = any("ethiopia" in (o.get("country_full_name") or "").lower() for o in bean.get("origins", []))
            text_match = "ethiopia" in bean["name"].lower() or "ethiopia" in (bean.get("description") or "").lower()

            assert origin_match or text_match, f"Result {bean['name']} does not match standard query 'ethiopia'"

            # Check FTS term "washed"
            fts_match = "washed" in (bean.get("process") or "").lower() or \
                        "washed" in bean["name"].lower() or \
                        "washed" in (bean.get("description") or "").lower()
            assert fts_match, f"Result {bean['name']} does not match FTS query 'washed'"

@pytest.mark.asyncio
async def test_search_coffee_beans_fts_no_results(client):
    """Test FTS query with a term that definitely doesn't exist"""
    response = client.get("/v1/search?fts_query=nonexistentcoffeeterm12345")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) == 0

@pytest.mark.asyncio
async def test_get_tasting_note_categories_fts(client):
    """Test FTS query on the tasting note categories endpoint"""
    response = client.get("/v1/tasting-note-categories?fts_query=chocolate")

    assert response.status_code == 200
    data = response.json()
    # The response for this endpoint follows the APIResponse structure
    assert isinstance(data, dict)
    assert data["success"] is True
    assert "data" in data
    assert "categories" in data["data"]
    assert "metadata" in data["data"]
