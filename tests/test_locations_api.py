"""Tests for the locations API endpoint."""
import pytest
from fastapi.testclient import TestClient

from kissaten.api.main import app

client = TestClient(app)


def test_get_location_detail_uk():
    """Test getting UK location details."""
    response = client.get("/v1/roasted-in/united-kingdom")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert "data" in data

    location = data["data"]
    assert location["location_name"] == "United Kingdom"
    assert location["location_type"] == "country"
    assert "statistics" in location
    assert location["statistics"]["roaster_count"] > 0


def test_get_location_detail_europe():
    """Test getting Europe region details."""
    response = client.get("/v1/roasted-in/europe")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert "data" in data

    location = data["data"]
    assert location["location_name"] == "Europe"
    assert location["location_type"] == "region"
    assert "statistics" in location
    assert location["statistics"]["roaster_count"] > 0


def test_get_location_detail_not_found():
    """Test getting a location that doesn't exist."""
    response = client.get("/v1/roasted-in/nonexistent-location")
    assert response.status_code == 404


def test_location_statistics_structure():
    """Test that location statistics have the expected structure."""
    response = client.get("/v1/roasted-in/united-kingdom")
    assert response.status_code == 200

    location = response.json()["data"]
    stats = location["statistics"]

    assert "available_beans" in stats
    assert "total_beans" in stats
    assert "roaster_count" in stats
    assert "city_count" in stats
    assert stats["city_count"] is not None or stats.get("country_count") is not None


def test_location_top_roasters():
    """Test that location includes top roasters."""
    response = client.get("/v1/roasted-in/united-kingdom")
    assert response.status_code == 200

    location = response.json()["data"]

    assert "top_roasters" in location
    if len(location["top_roasters"]) > 0:
        roaster = location["top_roasters"][0]
        assert "name" in roaster
        assert "slug" in roaster
        assert "available_beans" in roaster
        assert "total_beans" in roaster
        assert "country_code" in roaster


def test_location_varietals_and_origins():
    """Test that location includes varietals and origins."""
    response = client.get("/v1/roasted-in/united-kingdom")
    assert response.status_code == 200

    location = response.json()["data"]

    assert "varietals" in location
    assert "top_origins" in location
    assert isinstance(location["varietals"], list)
    assert isinstance(location["top_origins"], list)


def test_location_hierarchy_fields():
    """Test that location hierarchy fields are present."""
    # Test country - should have region info
    response = client.get("/v1/roasted-in/united-kingdom")
    assert response.status_code == 200

    data = response.json()["data"]
    assert data["location_type"] == "country"
    assert "location_slug" in data
    assert data["location_slug"] == "united-kingdom"
    assert "region_name" in data
    assert "region_slug" in data
    assert data["region_name"] == "Europe"
    assert data["region_slug"] == "europe"

    # Test region - should have countries list
    response = client.get("/v1/roasted-in/europe")
    assert response.status_code == 200

    data = response.json()["data"]
    assert data["location_type"] == "region"
    assert "location_slug" in data
    assert data["location_slug"] == "europe"
    assert "countries" in data
    assert isinstance(data["countries"], list)

    # Check country structure if any exist
    if len(data["countries"]) > 0:
        country = data["countries"][0]
        assert "name" in country
        assert "slug" in country
        assert "roaster_count" in country
        assert "available_beans" in country
        assert "total_beans" in country

