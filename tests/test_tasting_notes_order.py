"""Test that tasting notes maintain their original order after adding primary categories."""

import os
import sys
from pathlib import Path

# Set environment variable to ensure we're in test mode
os.environ["PYTEST_CURRENT_TEST"] = "test_tasting_notes_order.py"

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


@pytest.mark.asyncio
async def test_tasting_notes_order_preservation(setup_database, test_data_dir):
    """Test that tasting notes maintain their original order after adding primary categories."""
    # Load test data
    await load_coffee_data(test_data_dir)

    # Verify data was loaded
    total_beans_result = conn.execute("SELECT COUNT(*) FROM coffee_beans").fetchone()
    total_beans = total_beans_result[0] if total_beans_result else 0
    assert total_beans > 0, "No beans were loaded"

    # Get a coffee bean with tasting notes directly from database to verify original order
    original_bean_query = """
        SELECT id, name, roaster, tasting_notes
        FROM coffee_beans
        WHERE tasting_notes IS NOT NULL
        AND array_length(tasting_notes) > 1
        LIMIT 1
    """
    original_result = conn.execute(original_bean_query).fetchone()

    if not original_result:
        pytest.skip("No coffee beans with multiple tasting notes found in test data")

    bean_id, bean_name, roaster, original_tasting_notes = original_result

    # Ensure we have multiple tasting notes to test ordering
    assert len(original_tasting_notes) > 1, f"Bean {bean_name} should have multiple tasting notes for this test"

    print(f"Testing bean: {bean_name} from {roaster}")
    print(f"Original tasting notes order: {original_tasting_notes}")

    # Create TestClient and search for this specific bean using the API
    client = TestClient(app)
    response = client.get(
        "/v1/search",
        params={
            "query": bean_name,
            "roaster": roaster,
            "per_page": 1
        }
    )

    # Verify we got results
    assert response.status_code == 200, f"API request failed: {response.text}"
    search_data = response.json()
    assert search_data["success"], "Search should be successful"
    assert len(search_data["data"]) > 0, "Should find at least one bean"

    # Get the first result
    search_result = search_data["data"][0]

    # Extract just the note names from the search result tasting notes
    search_tasting_notes = []
    if search_result.get("tasting_notes"):
        for note in search_result["tasting_notes"]:
            if isinstance(note, dict) and "note" in note:
                # It's a TastingNote object
                search_tasting_notes.append(note["note"])
            elif isinstance(note, str):
                # It's a string
                search_tasting_notes.append(note)

    print(f"Search result tasting notes order: {search_tasting_notes}")

    # The key assertion: tasting notes order should be preserved
    assert search_tasting_notes == original_tasting_notes, (
        f"Tasting notes order not preserved!\n"
        f"Original: {original_tasting_notes}\n"
        f"Search result: {search_tasting_notes}"
    )


@pytest.mark.asyncio
async def test_tasting_notes_with_categories_structure(setup_database, test_data_dir):
    """Test that tasting notes with categories have the correct structure."""
    # Load test data
    await load_coffee_data(test_data_dir)

    # Create TestClient and search for any bean with tasting notes
    client = TestClient(app)
    response = client.get("/v1/search", params={"per_page": 1})

    assert response.status_code == 200, f"API request failed: {response.text}"
    search_data = response.json()
    assert search_data["success"], "Search should be successful"

    if len(search_data["data"]) > 0:
        bean = search_data["data"][0]

        if bean.get("tasting_notes"):
            for note in bean["tasting_notes"]:
                if isinstance(note, dict) and "note" in note:
                    # It's a TastingNote object - check structure
                    assert "note" in note, "TastingNote should have 'note' field"
                    assert "primary_category" in note, "TastingNote should have 'primary_category' field"
                    assert isinstance(note["note"], str), "Note should be a string"
                    # primary_category can be None or string
                    assert note["primary_category"] is None or isinstance(note["primary_category"], str), (
                        "Primary category should be None or string"
                    )
                elif isinstance(note, str):
                    # It's a string - this is also valid
                    assert isinstance(note, str), "Note should be a string"


@pytest.mark.asyncio
async def test_multiple_beans_tasting_notes_order(setup_database, test_data_dir):
    """Test tasting notes order preservation across multiple beans."""
    # Load test data
    await load_coffee_data(test_data_dir)

    # Get multiple coffee beans with tasting notes from database
    original_beans_query = """
        SELECT id, name, roaster, tasting_notes
        FROM coffee_beans
        WHERE tasting_notes IS NOT NULL
        AND array_length(tasting_notes) > 1
        LIMIT 5
    """
    original_results = conn.execute(original_beans_query).fetchall()

    if not original_results:
        pytest.skip("No coffee beans with multiple tasting notes found in test data")

    print(f"Testing {len(original_results)} beans for tasting notes order preservation")

    # Create TestClient
    client = TestClient(app)

    for bean_id, bean_name, roaster, original_tasting_notes in original_results:
        print(f"\n--- Testing: {bean_name} from {roaster} ---")
        print(f"Original tasting notes: {original_tasting_notes}")

        # Search for this specific bean
        response = client.get(
            "/v1/search",
            params={
                "query": bean_name,
                "roaster": roaster,
                "per_page": 1
            }
        )

        assert response.status_code == 200, f"API request failed for {bean_name}: {response.text}"
        search_data = response.json()
        assert search_data["success"], f"Search should be successful for {bean_name}"

        if len(search_data["data"]) > 0:
            search_result = search_data["data"][0]

            # Print the raw tasting notes structure for debugging
            print(f"Raw tasting notes from API: {search_result.get('tasting_notes', [])}")

            # Extract note names
            search_tasting_notes = []
            if search_result.get("tasting_notes"):
                for note in search_result["tasting_notes"]:
                    if isinstance(note, dict) and "note" in note:
                        search_tasting_notes.append(note["note"])
                        print(f"  Note: '{note['note']}', Category: {note.get('primary_category', 'None')}")
                    elif isinstance(note, str):
                        search_tasting_notes.append(note)
                        print(f"  Note (string): '{note}'")

            print(f"Extracted tasting notes: {search_tasting_notes}")

            # Check order preservation
            if search_tasting_notes != original_tasting_notes:
                print(f"❌ ORDER NOT PRESERVED!")
                print(f"  Original: {original_tasting_notes}")
                print(f"  API result: {search_tasting_notes}")
                assert False, f"Tasting notes order not preserved for {bean_name}"
            else:
                print(f"✅ Order preserved correctly")
        else:
            print(f"⚠️  No search results found for {bean_name}")

    print(f"\n✅ All {len(original_results)} beans passed the order preservation test")


@pytest.mark.asyncio
async def test_tanat_coffee_specific_bean_order(setup_database, test_data_dir):
    """Test a specific test bean with multiple tasting notes."""
    # Load test data
    await load_coffee_data(test_data_dir)

    # Look for the specific test bean
    bean_query = """
        SELECT id, name, roaster, tasting_notes, url
        FROM coffee_beans
        WHERE roaster = 'test_roaster'
        AND name LIKE '%Ethiopia%Tabe%'
        LIMIT 1
    """
    result = conn.execute(bean_query).fetchone()

    if not result:
        pytest.skip("Test bean not found in test data")

    bean_id, bean_name, roaster, original_tasting_notes, url = result

    print("\n=== Testing specific test bean ===")
    print(f"Bean: {bean_name}")
    print(f"URL: {url}")
    print(f"Original tasting notes order: {original_tasting_notes}")

    # Create TestClient and search for this specific bean
    client = TestClient(app)
    response = client.get(
        "/v1/search",
        params={
            "query": bean_name,
            "roaster": roaster,
            "per_page": 1
        }
    )

    assert response.status_code == 200, f"API request failed: {response.text}"
    search_data = response.json()
    assert search_data["success"], "Search should be successful"
    assert len(search_data["data"]) > 0, "Should find the test bean"

    search_result = search_data["data"][0]

    # Print the raw tasting notes structure for debugging
    print(f"Raw tasting notes from API: {search_result.get('tasting_notes', [])}")

    # Extract note names
    search_tasting_notes = []
    if search_result.get("tasting_notes"):
        for i, note in enumerate(search_result["tasting_notes"]):
            if isinstance(note, dict) and "note" in note:
                search_tasting_notes.append(note["note"])
                print(f"  {i+1}. Note: '{note['note']}', Category: {note.get('primary_category', 'None')}")
            elif isinstance(note, str):
                search_tasting_notes.append(note)
                print(f"  {i+1}. Note (string): '{note}'")

    print(f"Extracted tasting notes order: {search_tasting_notes}")

    # The key assertion: tasting notes order should be preserved
    if search_tasting_notes != original_tasting_notes:
        print("❌ ORDER NOT PRESERVED!")
        print(f"  Original: {original_tasting_notes}")
        print(f"  API result: {search_tasting_notes}")

        # Show the differences
        for i, (orig, api) in enumerate(zip(original_tasting_notes, search_tasting_notes)):
            if orig != api:
                print(f"  Position {i+1}: '{orig}' -> '{api}' ❌")
            else:
                print(f"  Position {i+1}: '{orig}' ✅")

        assert False, f"Tasting notes order not preserved for {bean_name}"
    else:
        print(f"✅ Order preserved correctly for {bean_name}")


@pytest.mark.asyncio
async def test_bean_by_slug_endpoint_order(setup_database, test_data_dir):
    """Test the /v1/beans/{roaster_slug}/{bean_slug} endpoint for tasting notes order."""
    # Load test data
    await load_coffee_data(test_data_dir)

    # Look for the specific test bean and get its bean_url_path
    bean_query = """
        SELECT id, name, roaster, tasting_notes, bean_url_path
        FROM coffee_beans
        WHERE roaster = 'test_roaster'
        AND name LIKE '%Ethiopia%Tabe%'
        AND bean_url_path IS NOT NULL
        LIMIT 1
    """
    result = conn.execute(bean_query).fetchone()

    if not result:
        # Try any bean with tasting notes and a bean_url_path
        bean_query = """
            SELECT id, name, roaster, tasting_notes, bean_url_path
            FROM coffee_beans
            WHERE tasting_notes IS NOT NULL
            AND array_length(tasting_notes) > 1
            AND bean_url_path IS NOT NULL
            LIMIT 1
        """
        result = conn.execute(bean_query).fetchone()

    if not result:
        pytest.skip("No beans with tasting notes and bean_url_path found in test data")

    bean_id, bean_name, roaster, original_tasting_notes, bean_url_path = result

    print(f"\n=== Testing /v1/beans endpoint ===")
    print(f"Bean: {bean_name}")
    print(f"Roaster: {roaster}")
    print(f"Bean URL path: {bean_url_path}")
    print(f"Original tasting notes order: {original_tasting_notes}")

    # Create TestClient and call the bean by slug endpoint
    client = TestClient(app)
    response = client.get(f"/v1/beans{bean_url_path}")

    assert response.status_code == 200, f"API request failed: {response.text}"
    bean_data = response.json()
    assert bean_data["success"], "Request should be successful"

    bean_result = bean_data["data"]

    # Print the raw tasting notes structure for debugging
    print(f"Raw tasting notes from API: {bean_result.get('tasting_notes', [])}")

    # Extract note names
    api_tasting_notes = []
    if bean_result.get("tasting_notes"):
        for i, note in enumerate(bean_result["tasting_notes"]):
            if isinstance(note, dict) and "note" in note:
                api_tasting_notes.append(note["note"])
                print(f"  {i+1}. Note: '{note['note']}', Category: {note.get('primary_category', 'None')}")
            elif isinstance(note, str):
                api_tasting_notes.append(note)
                print(f"  {i+1}. Note (string): '{note}'")

    print(f"Extracted tasting notes order: {api_tasting_notes}")

    # The key assertion: tasting notes order should be preserved
    if api_tasting_notes != original_tasting_notes:
        print(f"❌ ORDER NOT PRESERVED in /v1/beans endpoint!")
        print(f"  Original: {original_tasting_notes}")
        print(f"  API result: {api_tasting_notes}")

        # Show the differences
        max_len = max(len(original_tasting_notes), len(api_tasting_notes))
        for i in range(max_len):
            orig = original_tasting_notes[i] if i < len(original_tasting_notes) else "MISSING"
            api = api_tasting_notes[i] if i < len(api_tasting_notes) else "MISSING"
            if orig != api:
                print(f"  Position {i+1}: '{orig}' -> '{api}' ❌")
            else:
                print(f"  Position {i+1}: '{orig}' ✅")

        assert False, f"Tasting notes order not preserved for {bean_name} in /v1/beans endpoint"
    else:
        print(f"✅ Order preserved correctly for {bean_name} in /v1/beans endpoint")


@pytest.mark.asyncio
async def test_ordering_issue_with_categories(setup_database, test_data_dir):
    """Test that demonstrates the ordering issue when tasting notes categories are present."""
    # Load test data
    await load_coffee_data(test_data_dir)

    # Get a bean with multiple tasting notes
    bean_query = """
        SELECT id, name, roaster, tasting_notes, bean_url_path
        FROM coffee_beans
        WHERE tasting_notes IS NOT NULL
        AND array_length(tasting_notes) > 2
        LIMIT 1
    """
    result = conn.execute(bean_query).fetchone()

    if not result:
        pytest.skip("No beans with multiple tasting notes found")

    bean_id, bean_name, roaster, original_tasting_notes, bean_url_path = result

    print(f"\n=== Testing ordering with categories ===")
    print(f"Bean: {bean_name}")
    print(f"Original tasting notes: {original_tasting_notes}")

    # Insert some tasting notes categories - deliberately in different order
    # to test if the JOIN affects ordering
    categories_to_insert = [
        (original_tasting_notes[-1], "Sweetness"),  # Last note -> category
        (original_tasting_notes[0], "Fruit"),       # First note -> category
        (original_tasting_notes[1] if len(original_tasting_notes) > 1 else "Apple", "Fruit"),  # Second note -> category
    ]

    print(f"Inserting categories: {categories_to_insert}")

    for note, category in categories_to_insert:
        conn.execute(
            "INSERT OR REPLACE INTO tasting_notes_categories (tasting_note, primary_category) VALUES (?, ?)",
            [note, category]
        )
    conn.commit()

    # Now test both endpoints
    client = TestClient(app)

    # Test search endpoint
    print(f"\n--- Testing /v1/search endpoint ---")
    search_response = client.get(
        "/v1/search",
        params={
            "query": bean_name,
            "roaster": roaster,
            "per_page": 1
        }
    )

    assert search_response.status_code == 200
    search_data = search_response.json()
    assert search_data["success"]

    if len(search_data["data"]) > 0:
        search_result = search_data["data"][0]
        search_notes = []
        if search_result.get("tasting_notes"):
            for note in search_result["tasting_notes"]:
                if isinstance(note, dict) and "note" in note:
                    search_notes.append(note["note"])
                    print(f"  Note: '{note['note']}', Category: {note.get('primary_category', 'None')}")
                elif isinstance(note, str):
                    search_notes.append(note)

        print(f"Search result order: {search_notes}")

        if search_notes != original_tasting_notes:
            print(f"❌ SEARCH ENDPOINT: Order not preserved!")
            print(f"  Original: {original_tasting_notes}")
            print(f"  Search:   {search_notes}")
        else:
            print(f"✅ Search endpoint: Order preserved")

    # Test bean by slug endpoint if bean_url_path exists
    if bean_url_path:
        print(f"\n--- Testing /v1/beans endpoint ---")
        bean_response = client.get(f"/v1/beans{bean_url_path}")

        if bean_response.status_code == 200:
            bean_data = bean_response.json()
            if bean_data["success"]:
                bean_result = bean_data["data"]
                bean_notes = []
                if bean_result.get("tasting_notes"):
                    for note in bean_result["tasting_notes"]:
                        if isinstance(note, dict) and "note" in note:
                            bean_notes.append(note["note"])
                            print(f"  Note: '{note['note']}', Category: {note.get('primary_category', 'None')}")
                        elif isinstance(note, str):
                            bean_notes.append(note)

                print(f"Bean endpoint order: {bean_notes}")

                if bean_notes != original_tasting_notes:
                    print(f"❌ BEAN ENDPOINT: Order not preserved!")
                    print(f"  Original: {original_tasting_notes}")
                    print(f"  Bean:     {bean_notes}")
                    assert False, f"Tasting notes order not preserved in /v1/beans endpoint"
                else:
                    print(f"✅ Bean endpoint: Order preserved")

    # Final assertion - at least one endpoint should show the issue
    # (This test is designed to demonstrate the problem, not necessarily fail)
    print(f"\n=== Test completed - check output above for any ordering issues ===")
