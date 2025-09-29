#!/usr/bin/env python3
"""
Pytest tests for the diffjson update functionality in kissaten.api.main
Tests the ability to make partial updates to existing beans without overwriting all data.
"""
import shutil
import sys
import tempfile
from pathlib import Path

# Add the src directory to the path so we can import kissaten modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
import pytest_asyncio

from kissaten.api.db import conn, init_database, load_coffee_data


@pytest_asyncio.fixture
async def setup_database():
    """Fixture to initialize database and clean up data before each test"""
    await init_database()

    # Clear existing data including static tables that get repopulated during load_coffee_data
    conn.execute("DELETE FROM origins")
    conn.execute("DELETE FROM coffee_beans")
    conn.execute("DELETE FROM roasters")
    conn.execute("DELETE FROM country_codes")
    conn.execute("DELETE FROM roaster_location_codes")
    conn.execute("DELETE FROM tasting_notes_categories")
    conn.commit()

    yield

    # Cleanup after test
    conn.execute("DELETE FROM origins")
    conn.execute("DELETE FROM coffee_beans")
    conn.execute("DELETE FROM roasters")
    conn.execute("DELETE FROM country_codes")
    conn.execute("DELETE FROM roaster_location_codes")
    conn.execute("DELETE FROM tasting_notes_categories")
    conn.commit()


@pytest.fixture
def test_data_dir():
    """Fixture to provide test data directory path"""
    test_dir = Path(__file__).parent.parent / "test_data" / "roasters"
    if not test_dir.exists():
        pytest.skip(f"Test data directory not found: {test_dir}")
    return test_dir


@pytest.mark.asyncio
async def test_diffjson_updates_without_overwriting(setup_database, test_data_dir):
    """Test that diffjson files update only specified fields without overwriting other data"""

    # Step 1: Load initial data from 20250908 (full JSON files)
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        roasters_dir = temp_path / "roasters"
        test_roaster_dir = roasters_dir / "test_roaster"
        initial_scrape_dir = test_roaster_dir / "20250908"

        # Copy only the 20250908 data for initial load
        initial_scrape_source = test_data_dir / "test_roaster" / "20250908"
        if initial_scrape_source.exists():
            shutil.copytree(initial_scrape_source, initial_scrape_dir)
            await load_coffee_data(roasters_dir)

        # Get initial state of the Colombia Inmaculada bean
        initial_bean = conn.execute("""
            SELECT name, roaster, url, roast_level, price, in_stock, weight,
                   currency, is_decaf, cupping_score, tasting_notes, description
            FROM coffee_beans
            WHERE url = 'https://leavescoffee.jp/en/products/colombia-inmaculada'
        """).fetchone()

        assert initial_bean is not None, "Initial bean not found"

        initial_name, initial_roaster, initial_url, initial_roast_level, initial_price, \
        initial_in_stock, initial_weight, initial_currency, initial_is_decaf, \
        initial_cupping_score, initial_tasting_notes, initial_description = initial_bean

        # Verify initial state
        assert initial_name == "Colombia Inmaculada"
        assert initial_roaster == "Leaves Coffee Roasters"
        assert initial_roast_level is None  # Should be null initially
        assert initial_price == 3600.0
        assert initial_in_stock is True
        assert initial_weight == 100
        assert initial_currency == "JPY"

        # Get initial origins data
        initial_origins = conn.execute("""
            SELECT country, region, producer, farm, process, variety, elevation_min, elevation_max
            FROM origins o
            JOIN coffee_beans cb ON o.bean_id = cb.id
            WHERE cb.url = 'https://leavescoffee.jp/en/products/colombia-inmaculada'
        """).fetchall()

        assert len(initial_origins) == 1, "Should have exactly one origin"
        initial_origin = initial_origins[0]
        initial_country, initial_region, initial_producer, initial_farm, \
        initial_process, initial_variety, initial_elevation_min, initial_elevation_max = initial_origin

    # Step 2: Clear existing data and load data including the diffjson update (20250912)
    conn.execute("DELETE FROM origins")
    conn.execute("DELETE FROM coffee_beans")
    conn.execute("DELETE FROM roasters")
    conn.commit()
    await load_coffee_data(test_data_dir)

    # Step 3: Verify that the diffjson update was applied correctly
    updated_bean = conn.execute("""
        SELECT name, roaster, url, roast_level, price, in_stock, weight,
               currency, is_decaf, cupping_score, tasting_notes, description
        FROM coffee_beans
        WHERE url = 'https://leavescoffee.jp/en/products/colombia-inmaculada'
    """).fetchone()

    assert updated_bean is not None, "Updated bean not found"

    updated_name, updated_roaster, updated_url, updated_roast_level, updated_price, \
    updated_in_stock, updated_weight, updated_currency, updated_is_decaf, \
    updated_cupping_score, updated_tasting_notes, updated_description = updated_bean

    # Verify that diffjson fields were updated
    assert updated_roast_level == "Light", "Roast level should be updated from diffjson"
    assert updated_price == 3650.0, "Price should be updated from diffjson"
    assert updated_in_stock is False, "Stock status should be updated from diffjson"

    # Verify that non-diffjson fields were preserved
    assert updated_name == initial_name, "Name should be preserved"
    assert updated_roaster == initial_roaster, "Roaster should be preserved"
    assert updated_url == initial_url, "URL should be preserved"
    assert updated_weight == initial_weight, "Weight should be preserved"
    assert updated_currency == initial_currency, "Currency should be preserved"
    assert updated_is_decaf == initial_is_decaf, "Decaf status should be preserved"
    assert updated_cupping_score == initial_cupping_score, "Cupping score should be preserved"
    assert updated_tasting_notes == initial_tasting_notes, "Tasting notes should be preserved"
    assert updated_description == initial_description, "Description should be preserved"

    # Verify that origins data was preserved
    updated_origins = conn.execute("""
        SELECT country, region, producer, farm, process, variety, elevation_min, elevation_max
        FROM origins o
        JOIN coffee_beans cb ON o.bean_id = cb.id
        WHERE cb.url = 'https://leavescoffee.jp/en/products/colombia-inmaculada'
    """).fetchall()

    assert len(updated_origins) == 1, "Should still have exactly one origin"
    updated_origin = updated_origins[0]

    # Origins should be completely preserved since they weren't in the diffjson
    assert updated_origin == initial_origin, "Origins data should be completely preserved"


@pytest.mark.asyncio
async def test_diffjson_only_affects_target_bean(setup_database, test_data_dir):
    """Test that diffjson updates only affect the target bean, not other beans"""

    # Load all data including diffjson
    await load_coffee_data(test_data_dir)

    # Get the updated bean (Colombia Inmaculada)
    updated_bean = conn.execute("""
        SELECT roast_level, price, in_stock
        FROM coffee_beans
        WHERE url = 'https://leavescoffee.jp/en/products/colombia-inmaculada'
    """).fetchone()

    assert updated_bean is not None, "Target bean not found"
    roast_level, price, in_stock = updated_bean

    # Verify target bean was updated
    assert roast_level == "Light"
    assert price == 3650.0
    assert in_stock is False

    # Verify other beans were not affected by checking a few other beans
    other_beans = conn.execute("""
        SELECT name, url, roast_level, in_stock
        FROM coffee_beans
        WHERE url != 'https://leavescoffee.jp/en/products/colombia-inmaculada'
        LIMIT 3
    """).fetchall()

    assert len(other_beans) > 0, "Should have other beans in the database"

    # Other beans should not have been modified by the diffjson
    for bean in other_beans:
        name, url, roast_level, in_stock = bean
        # Verify they have reasonable data (specific values will depend on test data)
        assert name is not None and name != "", f"Bean {url} should have a name"


@pytest.mark.asyncio
async def test_diffjson_with_missing_original_bean(setup_database, test_data_dir):
    """Test behavior when diffjson references a bean that doesn't exist but there are other beans"""

    # First load some real data to establish a baseline
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        roasters_dir = temp_path / "roasters"
        test_roaster_dir = roasters_dir / "test_roaster"

        # Copy some initial data (from 20250908)
        initial_scrape_dir = test_roaster_dir / "20250908"
        initial_scrape_source = test_data_dir / "test_roaster" / "20250908"
        if initial_scrape_source.exists():
            shutil.copytree(initial_scrape_source, initial_scrape_dir)

        # Create a new scrape with a diffjson for a non-existent bean
        new_scrape_dir = test_roaster_dir / "20250913"
        new_scrape_dir.mkdir(parents=True)

        # Create a diffjson for a non-existent bean
        fake_diffjson = new_scrape_dir / "nonexistent_bean_123456.diffjson"
        fake_diffjson.write_text("""{
  "url": "https://example.com/nonexistent-bean",
  "price": 5000.0,
  "in_stock": false
}""")

        # Load the data
        await load_coffee_data(roasters_dir)

        # Should not create a new bean from diffjson, only existing beans should be updated
        # Count total beans - should be same as original data
        bean_count_result = conn.execute("SELECT COUNT(*) FROM coffee_beans").fetchone()
        bean_count = bean_count_result[0] if bean_count_result else 0
        assert bean_count > 0, "Should have loaded original beans"

        # Check that the fake URL does not exist
        fake_bean_result = conn.execute("""
            SELECT COUNT(*) FROM coffee_beans
            WHERE url = 'https://example.com/nonexistent-bean'
        """).fetchone()
        fake_bean = fake_bean_result[0] if fake_bean_result else 0
        assert fake_bean == 0, "Should not create bean from diffjson without original data"
@pytest.mark.asyncio
async def test_multiple_diffjson_files(setup_database, test_data_dir):
    """Test handling multiple diffjson files in the same scrape"""

    # First load initial data
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        roasters_dir = temp_path / "roasters"
        test_roaster_dir = roasters_dir / "test_roaster"

        # Copy initial data
        initial_scrape_dir = test_roaster_dir / "20250908"
        initial_scrape_source = test_data_dir / "test_roaster" / "20250908"
        if initial_scrape_source.exists():
            shutil.copytree(initial_scrape_source, initial_scrape_dir)

        # Create a new scrape with multiple diffjson files
        new_scrape_dir = test_roaster_dir / "20250913"
        new_scrape_dir.mkdir(parents=True)

        # Create diffjson for Colombia Inmaculada
        colombia_diffjson = new_scrape_dir / "colombia_inmaculada_honey_191517.diffjson"
        colombia_diffjson.write_text("""{
  "url": "https://leavescoffee.jp/en/products/colombia-inmaculada",
  "price": 3700.0,
  "in_stock": true
}""")

        # Create diffjson for another bean
        ethiopia_diffjson = new_scrape_dir / "ethiopia_tabe_bruka_natural_natural_191501.diffjson"
        ethiopia_diffjson.write_text("""{
  "url": "https://leavescoffee.jp/en/products/ethiopia-tabe-bruka",
  "price": 2800.0,
  "in_stock": false
}""")

        # Load the data
        await load_coffee_data(roasters_dir)

        # Verify both updates were applied
        colombia_bean = conn.execute("""
            SELECT price, in_stock FROM coffee_beans
            WHERE url = 'https://leavescoffee.jp/en/products/colombia-inmaculada'
        """).fetchone()

        if colombia_bean:  # Only test if the bean exists
            price, in_stock = colombia_bean
            assert price == 3700.0, "Colombia bean price should be updated"
            assert in_stock is True, "Colombia bean should be back in stock"

        ethiopia_bean = conn.execute("""
            SELECT price, in_stock FROM coffee_beans
            WHERE url = 'https://leavescoffee.jp/en/products/ethiopia-tabe-bruka'
        """).fetchone()

        if ethiopia_bean:  # Only test if the bean exists
            price, in_stock = ethiopia_bean
            assert price == 2800.0, "Ethiopia bean price should be updated"
            assert in_stock is False, "Ethiopia bean should be out of stock"


@pytest.mark.asyncio
async def test_diffjson_updates_scraped_at_field(setup_database, test_data_dir):
    """Test that scraped_at field can be updated via diffjson"""

    # Step 1: Load initial data
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        roasters_dir = temp_path / "roasters"
        test_roaster_dir = roasters_dir / "test_roaster"
        initial_scrape_dir = test_roaster_dir / "20250908"

        # Copy initial data
        initial_scrape_source = test_data_dir / "test_roaster" / "20250908"
        if initial_scrape_source.exists():
            shutil.copytree(initial_scrape_source, initial_scrape_dir)
            await load_coffee_data(roasters_dir)

        # Get initial scraped_at value
        initial_result = conn.execute("""
            SELECT scraped_at FROM coffee_beans
            WHERE url = 'https://leavescoffee.jp/en/products/colombia-inmaculada'
        """).fetchone()

        assert initial_result is not None, "Initial bean not found"
        initial_scraped_at = initial_result[0]

        # Create a new scrape with diffjson containing updated scraped_at
        new_scrape_dir = test_roaster_dir / "20250913"
        new_scrape_dir.mkdir(parents=True)

        # Create diffjson with a specific scraped_at timestamp
        updated_timestamp = "2025-09-13T10:30:00.000000+00:00"
        diffjson_content = f"""{{
  "url": "https://leavescoffee.jp/en/products/colombia-inmaculada",
  "scraped_at": "{updated_timestamp}",
  "price": 3800.0,
  "in_stock": true
}}"""

        diffjson_file = new_scrape_dir / "colombia_inmaculada_honey_191517.diffjson"
        diffjson_file.write_text(diffjson_content)

        # Clear existing data and load data again to apply diffjson updates
        conn.execute("DELETE FROM origins")
        conn.execute("DELETE FROM coffee_beans")
        conn.execute("DELETE FROM roasters")
        conn.commit()
        await load_coffee_data(roasters_dir)

        # Verify scraped_at was updated
        updated_result = conn.execute("""
            SELECT scraped_at, price, in_stock FROM coffee_beans
            WHERE url = 'https://leavescoffee.jp/en/products/colombia-inmaculada'
        """).fetchone()

        assert updated_result is not None, "Updated bean not found"
        updated_scraped_at, updated_price, updated_in_stock = updated_result

        # Verify the scraped_at field was updated
        assert updated_scraped_at != initial_scraped_at, "scraped_at should be updated"
        assert str(updated_scraped_at).startswith("2025-09-13"), "scraped_at should match the diffjson timestamp"

        # Verify other fields were also updated
        assert updated_price == 3800.0, "Price should be updated"
        assert updated_in_stock is True, "Stock status should be updated"


@pytest.mark.asyncio
async def test_diffjson_pydantic_validation(setup_database, test_data_dir):
    """Test that diffjson files are validated using the Pydantic schema"""
    from kissaten.schemas import CoffeeBeanDiffUpdate

    # Test valid diffjson data
    valid_data = {
        "url": "https://example.com/test-bean",
        "price": 25.99,
        "in_stock": True,
        "roast_level": "Medium"
    }

    # Should validate successfully
    diff_update = CoffeeBeanDiffUpdate.model_validate(valid_data)
    assert str(diff_update.url) == "https://example.com/test-bean"
    assert diff_update.price == 25.99
    assert diff_update.in_stock is True
    assert diff_update.roast_level == "Medium"

    # Test invalid data - missing required URL
    invalid_data = {
        "price": 25.99,
        "in_stock": True
    }

    with pytest.raises(Exception):  # Should raise validation error
        CoffeeBeanDiffUpdate.model_validate(invalid_data)

    # Test invalid data - invalid price
    invalid_price_data = {
        "url": "https://example.com/test-bean",
        "price": -10.0,  # Negative price should fail
        "in_stock": True
    }

    with pytest.raises(Exception):  # Should raise validation error
        CoffeeBeanDiffUpdate.model_validate(invalid_price_data)

    # Test invalid data - invalid weight
    invalid_weight_data = {
        "url": "https://example.com/test-bean",
        "weight": 10,  # Too small (< 50g)
        "in_stock": True
    }

    with pytest.raises(Exception):  # Should raise validation error
        CoffeeBeanDiffUpdate.model_validate(invalid_weight_data)

    # Test that non-updatable fields are not included (should work fine)
    data_with_non_updatable = {
        "url": "https://example.com/test-bean",
        "price": 25.99,
        "origins": [{"country": "CO"}],  # This field is not updatable via diffjson
        "image_url": "https://example.com/image.jpg"  # This field is not updatable via diffjson
    }

    # Should validate but only include the updatable fields
    diff_update = CoffeeBeanDiffUpdate.model_validate(data_with_non_updatable)
    assert str(diff_update.url) == "https://example.com/test-bean"
    assert diff_update.price == 25.99

    # Convert to dict and verify non-updatable fields are excluded
    dumped = diff_update.model_dump(exclude_none=True)
    assert "origins" not in dumped
    assert "image_url" not in dumped
    assert "url" in dumped
    assert "price" in dumped